"""
Vantage chat service — orchestrates conversation flow.

Responsibilities:
  1. Load recommendation + profile (the persistent context)
  2. Load chat history (last N turns)
  3. Build the Groq messages payload, including any image attachment
  4. Pick the right model (vision when an image is present, text otherwise)
  5. Call Groq, persist user message + assistant response, return them
"""
from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.llm import client as groq
from app.llm.client import GroqError
from app.models.chat import ChatMessage
from app.models.profile import Profile
from app.models.recommendation import Recommendation
from app.services.chat.attachments import ProcessedAttachment
from app.services.chat.prompts import (
    VANTAGE_SYSTEM_PROMPT,
    build_attachment_note,
    build_context_block,
)

logger = logging.getLogger(__name__)

# Keep history bounded to control prompt cost; older messages drop off
_MAX_HISTORY_TURNS = 12

# Cap response length so a runaway model doesn't blow tokens
_MAX_RESPONSE_TOKENS = 800


async def load_history(
    recommendation_id: uuid.UUID, db: AsyncSession
) -> list[ChatMessage]:
    """Return ChatMessage rows for *recommendation_id* in chronological order."""
    rows = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.recommendation_id == recommendation_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return list(rows.scalars().all())


async def _load_recommendation_with_profile(
    recommendation_id: uuid.UUID, db: AsyncSession
) -> tuple[Recommendation, Profile]:
    """Load the recommendation + its source profile, or raise ValueError."""
    rec_row = await db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    )
    rec = rec_row.scalar_one_or_none()
    if rec is None:
        raise ValueError("recommendation_not_found")

    prof_row = await db.execute(
        select(Profile).where(Profile.id == rec.profile_id)
    )
    profile = prof_row.scalar_one_or_none()
    if profile is None:
        raise ValueError("profile_not_found")

    return rec, profile


def _profile_to_dict(profile: Profile) -> dict:
    return {
        "skills": profile.skills,
        "interests": profile.interests,
        "education_level": profile.education_level,
        "personality": profile.personality,
    }


def _build_messages(
    *,
    profile: Profile,
    recommendation: Recommendation,
    history: list[ChatMessage],
    user_text: str,
    attachment: ProcessedAttachment | None,
) -> tuple[list[dict], bool]:
    """
    Assemble the Groq messages list.

    Returns (messages, has_image). When has_image is True the caller must
    use a vision-capable model.
    """
    profile_dict = _profile_to_dict(profile)
    context = build_context_block(profile_dict, recommendation.result)

    messages: list[dict] = [
        {
            "role": "system",
            "content": f"{VANTAGE_SYSTEM_PROMPT}\n\n{context}",
        }
    ]

    # Truncate history to the last N turns
    trimmed = history[-_MAX_HISTORY_TURNS:]
    for m in trimmed:
        # Reattach the doc excerpt note so the LLM still sees what was sent
        prefix = build_attachment_note(m.attachment_kind, m.attachment_name, m.attachment_excerpt)
        messages.append(
            {
                "role": m.role,
                "content": f"{prefix}{m.content}" if prefix else m.content,
            }
        )

    has_image = attachment is not None and attachment.kind == "image"
    user_text_with_doc = user_text
    if attachment and attachment.kind != "image":
        user_text_with_doc = (
            build_attachment_note(attachment.kind, attachment.name, attachment.excerpt)
            + user_text
        )

    if has_image:
        # Multimodal message: text + inline image (Groq is OpenAI-compatible)
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_text or "Please analyse this image."},
                    {
                        "type": "image_url",
                        "image_url": {"url": attachment.image_data_url},  # type: ignore[union-attr]
                    },
                ],
            }
        )
    else:
        messages.append({"role": "user", "content": user_text_with_doc})

    return messages, has_image


async def send_message(
    *,
    recommendation_id: uuid.UUID,
    user_text: str,
    attachment: ProcessedAttachment | None,
    db: AsyncSession,
) -> ChatMessage:
    """
    Run one chat turn end-to-end.

    Persists the user message, calls Groq, persists the assistant
    response, returns the assistant ChatMessage row.
    """
    rec, profile = await _load_recommendation_with_profile(recommendation_id, db)

    history = await load_history(recommendation_id, db)
    messages, has_image = _build_messages(
        profile=profile,
        recommendation=rec,
        history=history,
        user_text=user_text,
        attachment=attachment,
    )

    model = settings.groq_model_chat_vision if has_image else settings.groq_model_chat
    logger.info(
        "vantage: rec=%s history=%d attachment=%s vision=%s",
        recommendation_id,
        len(history),
        attachment.kind if attachment else "none",
        has_image,
    )

    try:
        raw = await groq.chat_completion(
            model=model,
            messages=messages,
            temperature=0.5,
            max_tokens=_MAX_RESPONSE_TOKENS,
        )
    except GroqError:
        # Re-raise so the router can return a 502 with a sensible body
        raise

    assistant_text = raw["choices"][0]["message"]["content"].strip()

    # Persist both messages atomically
    user_msg = ChatMessage(
        recommendation_id=recommendation_id,
        role="user",
        content=user_text,
        attachment_kind=attachment.kind if attachment else None,
        attachment_name=attachment.name if attachment else None,
        attachment_excerpt=attachment.excerpt if attachment else None,
    )
    assistant_msg = ChatMessage(
        recommendation_id=recommendation_id,
        role="assistant",
        content=assistant_text,
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()
    await db.refresh(assistant_msg)

    return assistant_msg
