"""
O*NET database ingestion script for Echelon v2.

Usage (from repo root):
    make ingest-onet ONET_DIR=/path/to/extracted/onet/db_29_0_text

    # or directly inside the container:
    docker compose exec backend python scripts/ingest_onet.py --data-dir /data/onet

Download the O*NET database (free, no API key):
    https://www.onetcenter.org/database.html
    → "All Files" → "Text" format → extract the zip

Required files in --data-dir:
    Occupation Data.txt
    Skills.txt
    Work Styles.txt
    Job Zones.txt

=== FILTER RULES ===
1. Keep only .00 SOC suffix codes (base occupations; sub-specialties like .01 are
   O*NET-specific expansions and create messy duplicate entries).
2. Keep SOC major groups:
     11  Management
     13  Business & Financial Operations
     15  Computer & Mathematical
     17  Architecture & Engineering
     19  Life, Physical & Social Science
     21  Community & Social Service
     23  Legal
     25  Educational Instruction & Library
     27  Arts, Design, Entertainment, Sports & Media
     29  Healthcare Practitioners & Technical
     41  Sales & Related  (Job Zone filter removes low-skill sales automatically)
3. Exclude major groups: 31 (Healthcare Support), 33 (Protective Service),
   35 (Food Preparation), 37 (Building/Grounds), 39 (Personal Care),
   43 (Office/Admin Support), 45 (Farming/Fishing/Forestry),
   47 (Construction/Extraction), 49 (Installation/Maintenance/Repair),
   51 (Production), 53 (Transportation/Material Moving).
4. Keep only Job Zones 3, 4, 5 (medium to high preparation required).
5. If > 250 remain after all filters, trim to 250 alphabetically by title.

=== WORK STYLES → BIG FIVE MAPPING ===
O*NET Work Styles are NOT Big Five personality traits. This mapping is a heuristic
approximation intended to seed plausible values into the personality_fit column.
It is NOT a validated psychometric instrument.

  Conscientiousness ← Achievement/Effort, Persistence, Dependability,
                       Attention to Detail
  Openness          ← Innovation, Analytical Thinking, Adaptability/Flexibility,
                       Initiative
  Extraversion      ← Leadership, Social Orientation
  Agreeableness     ← Cooperation, Concern for Others
  Neuroticism       ← INVERTED: 100 − mean(Self-Control, Stress Tolerance)
                       (high self-control / stress tolerance = low neuroticism)

  O*NET Importance scores are 1.0–5.0; scaled to 0–100 by (score − 1) / 4 × 100.
  If an occupation has no data for a style group, the category-level default is used.
  If the category also has no default, FALLBACK_PERSONALITY is used.

=== GROWTH POTENTIAL ===
All O*NET careers are assigned growth_potential = "medium" by default.
Real growth data requires BLS Employment Projections (separate dataset).
TODO: enrich with BLS projections in a future pass.

=== LICENSE ===
O*NET content is licensed under CC BY 4.0. Attribution required:
"This product uses data from O*NET OnLine by the U.S. Department of Labor,
Employment and Training Administration (USDOL/ETA). O*NET® is a trademark
of USDOL/ETA."
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import re
import sys
import uuid
from pathlib import Path

# ── Make `app.*` importable when run as a standalone script ──────────────────
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd  # noqa: E402  (after sys.path manipulation)
from sqlalchemy import select  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.models.career import Career  # noqa: E402

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SOC major-group → keep/skip config
# ---------------------------------------------------------------------------

KEEP_GROUPS = {"11", "13", "15", "17", "19", "21", "23", "25", "27", "29", "41"}

SOC_CATEGORY = {
    "11": "Management",
    "13": "Business & Financial Operations",
    "15": "Computer & Mathematical",
    "17": "Architecture & Engineering",
    "19": "Life, Physical & Social Science",
    "21": "Community & Social Service",
    "23": "Legal",
    "25": "Educational Instruction & Library",
    "27": "Arts, Design, Entertainment & Media",
    "29": "Healthcare Practitioners & Technical",
    "41": "Sales & Related",
}

MAX_OCCUPATIONS = 250

# ---------------------------------------------------------------------------
# Work Styles → Big Five mapping
# ---------------------------------------------------------------------------

BIG_FIVE_STYLES: dict[str, list[str]] = {
    "conscientiousness": [
        "Achievement/Effort",
        "Persistence",
        "Dependability",
        "Attention to Detail",
    ],
    "openness": [
        "Innovation",
        "Analytical Thinking",
        "Adaptability/Flexibility",
        "Initiative",
    ],
    "extraversion": [
        "Leadership",
        "Social Orientation",
    ],
    "agreeableness": [
        "Cooperation",
        "Concern for Others",
    ],
    # This trait is INVERTED: high self-control / stress tolerance = low neuroticism
    "_neuroticism_inv": [
        "Self-Control",
        "Stress Tolerance",
    ],
}

# Sensible category-level defaults (used when an occupation has no Work Styles data)
CATEGORY_PERSONALITY_DEFAULTS: dict[str, dict[str, int]] = {
    "Management": {
        "openness": 65, "conscientiousness": 75, "extraversion": 70,
        "agreeableness": 65, "neuroticism": 35,
    },
    "Business & Financial Operations": {
        "openness": 60, "conscientiousness": 80, "extraversion": 55,
        "agreeableness": 60, "neuroticism": 35,
    },
    "Computer & Mathematical": {
        "openness": 72, "conscientiousness": 78, "extraversion": 38,
        "agreeableness": 55, "neuroticism": 32,
    },
    "Architecture & Engineering": {
        "openness": 68, "conscientiousness": 82, "extraversion": 42,
        "agreeableness": 58, "neuroticism": 30,
    },
    "Life, Physical & Social Science": {
        "openness": 80, "conscientiousness": 75, "extraversion": 48,
        "agreeableness": 62, "neuroticism": 35,
    },
    "Community & Social Service": {
        "openness": 65, "conscientiousness": 70, "extraversion": 65,
        "agreeableness": 80, "neuroticism": 40,
    },
    "Legal": {
        "openness": 65, "conscientiousness": 82, "extraversion": 58,
        "agreeableness": 55, "neuroticism": 38,
    },
    "Educational Instruction & Library": {
        "openness": 72, "conscientiousness": 75, "extraversion": 62,
        "agreeableness": 72, "neuroticism": 38,
    },
    "Arts, Design, Entertainment & Media": {
        "openness": 85, "conscientiousness": 60, "extraversion": 58,
        "agreeableness": 60, "neuroticism": 42,
    },
    "Healthcare Practitioners & Technical": {
        "openness": 62, "conscientiousness": 82, "extraversion": 55,
        "agreeableness": 75, "neuroticism": 38,
    },
    "Sales & Related": {
        "openness": 60, "conscientiousness": 68, "extraversion": 78,
        "agreeableness": 65, "neuroticism": 38,
    },
}

FALLBACK_PERSONALITY: dict[str, int] = {
    "openness": 60, "conscientiousness": 65, "extraversion": 50,
    "agreeableness": 60, "neuroticism": 40,
}

# ---------------------------------------------------------------------------
# File loading helpers
# ---------------------------------------------------------------------------

REQUIRED_FILES = [
    "Occupation Data.txt",
    "Skills.txt",
    "Work Styles.txt",
    "Job Zones.txt",
]


def _read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", dtype=str, encoding="latin-1")


def _col(df: pd.DataFrame, name: str) -> str:
    """Return the actual column name, stripping BOM and surrounding whitespace."""
    for col in df.columns:
        if col.strip("\ufeff").strip() == name:
            return col
    raise KeyError(f"Column '{name}' not found. Available: {list(df.columns)}")


def load_occupations(data_dir: Path) -> pd.DataFrame:
    df = _read_tsv(data_dir / "Occupation Data.txt")
    code_col = _col(df, "O*NET-SOC Code")
    title_col = _col(df, "Title")
    desc_col = _col(df, "Description")

    df = df.rename(columns={code_col: "soc_code", title_col: "title", desc_col: "description"})
    df = df[["soc_code", "title", "description"]].copy()
    df["soc_code"] = df["soc_code"].str.strip()
    df["title"] = df["title"].str.strip()
    df["description"] = df["description"].str.strip()
    return df


def load_skills(data_dir: Path) -> pd.DataFrame:
    df = _read_tsv(data_dir / "Skills.txt")
    code_col = _col(df, "O*NET-SOC Code")
    name_col = _col(df, "Element Name")
    scale_col = _col(df, "Scale ID")
    val_col = _col(df, "Data Value")

    df = df.rename(columns={
        code_col: "soc_code",
        name_col: "element_name",
        scale_col: "scale_id",
        val_col: "value",
    })
    df = df[["soc_code", "element_name", "scale_id", "value"]].copy()
    df = df[df["scale_id"] == "IM"]  # Importance scores only
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    return df


def load_work_styles(data_dir: Path) -> pd.DataFrame:
    df = _read_tsv(data_dir / "Work Styles.txt")
    code_col = _col(df, "O*NET-SOC Code")
    name_col = _col(df, "Element Name")
    scale_col = _col(df, "Scale ID")
    val_col = _col(df, "Data Value")

    df = df.rename(columns={
        code_col: "soc_code",
        name_col: "element_name",
        scale_col: "scale_id",
        val_col: "value",
    })
    df = df[["soc_code", "element_name", "scale_id", "value"]].copy()
    df = df[df["scale_id"] == "IM"]
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    return df


def load_job_zones(data_dir: Path) -> pd.DataFrame:
    df = _read_tsv(data_dir / "Job Zones.txt")
    code_col = _col(df, "O*NET-SOC Code")
    zone_col = _col(df, "Job Zone")

    df = df.rename(columns={code_col: "soc_code", zone_col: "job_zone"})
    df = df[["soc_code", "job_zone"]].copy()
    df["soc_code"] = df["soc_code"].str.strip()
    df["job_zone"] = pd.to_numeric(df["job_zone"], errors="coerce")
    return df.dropna(subset=["job_zone"])


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


def filter_occupations(
    occ_df: pd.DataFrame,
    zones_df: pd.DataFrame,
) -> pd.DataFrame:
    # 1. Keep only .00 suffix codes
    mask_base = occ_df["soc_code"].str.endswith(".00")

    # 2. Keep only target SOC major groups
    occ_df["major_group"] = occ_df["soc_code"].str[:2]
    mask_group = occ_df["major_group"].isin(KEEP_GROUPS)

    filtered = occ_df[mask_base & mask_group].copy()

    # 3. Merge with job zones and keep zones 3–5
    filtered = filtered.merge(zones_df[["soc_code", "job_zone"]], on="soc_code", how="left")
    filtered["job_zone"] = filtered["job_zone"].fillna(3)  # unknown → assume medium
    filtered = filtered[filtered["job_zone"] >= 3]

    # 4. Trim to MAX_OCCUPATIONS alphabetically
    if len(filtered) > MAX_OCCUPATIONS:
        filtered = filtered.sort_values("title").head(MAX_OCCUPATIONS)

    return filtered.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Per-occupation derivations
# ---------------------------------------------------------------------------


def _scale_to_100(value: float) -> int:
    """Convert O*NET 1–5 Importance score to 0–100 integer."""
    return round((value - 1.0) / 4.0 * 100)


def derive_skills(
    soc_code: str,
    skills_df: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    occ = skills_df[skills_df["soc_code"] == soc_code].sort_values("value", ascending=False)
    required = occ[occ["value"] >= 4.0]["element_name"].tolist()[:8]
    optional = occ[(occ["value"] >= 3.0) & (occ["value"] < 4.0)]["element_name"].tolist()[:8]
    return required, optional


def derive_personality(
    soc_code: str,
    styles_df: pd.DataFrame,
    category: str,
) -> dict[str, int]:
    occ = styles_df[styles_df["soc_code"] == soc_code]
    style_scores: dict[str, float] = dict(zip(occ["element_name"], occ["value"]))

    def trait_score(style_names: list[str]) -> int | None:
        vals = [style_scores[s] for s in style_names if s in style_scores]
        if not vals:
            return None
        return _scale_to_100(sum(vals) / len(vals))

    default = CATEGORY_PERSONALITY_DEFAULTS.get(category, FALLBACK_PERSONALITY)

    conscientiousness = trait_score(BIG_FIVE_STYLES["conscientiousness"])
    openness = trait_score(BIG_FIVE_STYLES["openness"])
    extraversion = trait_score(BIG_FIVE_STYLES["extraversion"])
    agreeableness = trait_score(BIG_FIVE_STYLES["agreeableness"])
    # Neuroticism is derived from inverted self-control/stress-tolerance
    inv_val = trait_score(BIG_FIVE_STYLES["_neuroticism_inv"])
    neuroticism = (100 - inv_val) if inv_val is not None else None

    return {
        "openness": openness if openness is not None else default["openness"],
        "conscientiousness": (
            conscientiousness if conscientiousness is not None else default["conscientiousness"]
        ),
        "extraversion": extraversion if extraversion is not None else default["extraversion"],
        "agreeableness": agreeableness if agreeableness is not None else default["agreeableness"],
        "neuroticism": neuroticism if neuroticism is not None else default["neuroticism"],
    }


def derive_difficulty(job_zone: float) -> str:
    if job_zone <= 2:
        return "low"
    if job_zone == 3:
        return "medium"
    return "high"  # zones 4 and 5


def make_slug(title: str, soc_code: str) -> str:
    title_part = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    code_part = soc_code.replace(".", "-")
    return f"{title_part}-{code_part}"


def truncate_description(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    return truncated[:last_space] + "…" if last_space > 0 else truncated


def external_url(soc_code: str) -> str:
    return f"https://www.onetonline.org/link/summary/{soc_code}"


# ---------------------------------------------------------------------------
# Database upsert
# ---------------------------------------------------------------------------


async def upsert_careers(
    records: list[dict],
    existing_manual_names: set[str],
) -> tuple[int, int, int]:
    added = updated = skipped = 0

    async with AsyncSessionLocal() as session:
        for rec in records:
            # Warn and skip if a manual career has the same name
            if rec["name"].lower() in {n.lower() for n in existing_manual_names}:
                logger.warning(
                    "Skipping O*NET '%s' — conflicts with an existing manual career by the same name.",
                    rec["name"],
                )
                skipped += 1
                continue

            result = await session.execute(
                select(Career).where(Career.onet_soc_code == rec["onet_soc_code"])
            )
            existing = result.scalar_one_or_none()

            if existing is not None:
                # Update mutable fields; preserve manual overrides to name/slug if any
                existing.description = rec["description"]
                existing.required_skills = rec["required_skills"]
                existing.optional_skills = rec["optional_skills"]
                existing.personality_fit = rec["personality_fit"]
                existing.difficulty = rec["difficulty"]
                existing.category = rec["category"]
                existing.external_url = rec["external_url"]
                updated += 1
            else:
                session.add(Career(**rec))
                added += 1

        await session.commit()

    return added, updated, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run(data_dir: Path) -> None:
    logger.info("Loading O*NET files from %s …", data_dir)

    missing = [f for f in REQUIRED_FILES if not (data_dir / f).exists()]
    if missing:
        logger.error(
            "Missing required file(s):\n%s\n\n"
            "Download the O*NET database from https://www.onetcenter.org/database.html\n"
            "and extract the zip. Then re-run with --data-dir pointing to the extracted folder.",
            "\n".join(f"  {data_dir / f}" for f in missing),
        )
        sys.exit(1)

    occ_df = load_occupations(data_dir)
    skills_df = load_skills(data_dir)
    styles_df = load_work_styles(data_dir)
    zones_df = load_job_zones(data_dir)

    logger.info("Loaded %d raw occupations; filtering …", len(occ_df))
    filtered = filter_occupations(occ_df, zones_df)
    logger.info("Filtered to %d occupations after group + Job Zone + cap rules.", len(filtered))

    # Fetch existing manual career names once, to detect conflicts
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Career.name).where(Career.source == "manual")
        )
        manual_names: set[str] = {row[0] for row in result.fetchall()}
    logger.info("Found %d existing manual careers to check for name conflicts.", len(manual_names))

    # Build career records
    records: list[dict] = []
    for _, row in filtered.iterrows():
        soc = row["soc_code"]
        title = row["title"]
        category = SOC_CATEGORY.get(row["major_group"], "Other")
        job_zone = float(row["job_zone"])

        required_skills, optional_skills = derive_skills(soc, skills_df)
        personality_fit = derive_personality(soc, styles_df, category)
        difficulty = derive_difficulty(job_zone)

        records.append({
            "id": uuid.uuid4(),
            "name": title,
            "slug": make_slug(title, soc),
            "description": truncate_description(row["description"]),
            "required_skills": required_skills,
            "optional_skills": optional_skills,
            "personality_fit": personality_fit,
            "difficulty": difficulty,
            "growth_potential": "medium",  # TODO: enrich with BLS projections
            "category": category,
            "source": "onet",
            "onet_soc_code": soc,
            "external_url": external_url(soc),
            "verified": True,
        })

    logger.info("Upserting %d O*NET career records …", len(records))
    added, updated, skipped = await upsert_careers(records, manual_names)

    async with AsyncSessionLocal() as session:
        total_result = await session.execute(select(Career).where(Career.deleted_at.is_(None)))
        total = len(total_result.scalars().all())

    print(
        f"\nO*NET ingestion complete.\n"
        f"  Added:   {added}\n"
        f"  Updated: {updated}\n"
        f"  Skipped: {skipped} (name conflicts with manual careers)\n"
        f"  Total active careers in DB: {total}\n"
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="Ingest O*NET database occupations into Echelon's careers table."
    )
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Path to the extracted O*NET database folder (e.g. db_29_0_text/).",
    )
    args = parser.parse_args()

    data_dir = args.data_dir
    if not data_dir.is_dir():
        logger.error(
            "'%s' is not a directory. Download the O*NET database from "
            "https://www.onetcenter.org/database.html and pass the extracted folder.",
            data_dir,
        )
        sys.exit(1)

    asyncio.run(run(data_dir))


if __name__ == "__main__":
    main()
