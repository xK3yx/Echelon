"use client";

/**
 * Vantage — floating career-counsellor chatbot.
 *
 * Mounts on the results page. Holds a persistent conversation tied to a
 * recommendation_id. Supports text messages plus PDF / DOCX / TXT / image
 * attachments. Conversation is server-persisted so refresh/reload restores
 * full history.
 */

import * as React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  Send,
  Paperclip,
  X,
  Loader2,
  FileText,
  Image as ImageIcon,
  AlertCircle,
} from "lucide-react";

import { api, ApiError } from "@/lib/api";
import type { ChatMessage, AttachmentKind } from "@/lib/types";
import { cn } from "@/lib/utils";

const MAX_FILE_SIZE_MB = 10;
const ALLOWED_MIME_PREFIXES = ["application/pdf", "application/vnd.", "text/plain", "image/"];

interface VantageProps {
  recommendationId: string;
}

export function Vantage({ recommendationId }: VantageProps) {
  const [open, setOpen] = React.useState(false);
  const [draft, setDraft] = React.useState("");
  const [attachment, setAttachment] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);
  const scrollRef = React.useRef<HTMLDivElement>(null);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["chat", recommendationId],
    queryFn: () => api.getChatHistory(recommendationId),
    enabled: open,
  });

  const messages = data?.messages ?? [];

  const sendMutation = useMutation({
    mutationFn: () =>
      api.sendChatMessage(recommendationId, draft.trim(), attachment),
    onSuccess: () => {
      setDraft("");
      setAttachment(null);
      setError(null);
      qc.invalidateQueries({ queryKey: ["chat", recommendationId] });
    },
    onError: (err) => {
      setError(
        err instanceof ApiError
          ? err.message
          : "Couldn't send message — please try again.",
      );
    },
  });

  // Auto-scroll the message list to the bottom whenever it grows
  React.useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length, sendMutation.isPending]);

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setError(`File exceeds ${MAX_FILE_SIZE_MB} MB limit.`);
      e.target.value = "";
      return;
    }
    if (!ALLOWED_MIME_PREFIXES.some((p) => f.type.startsWith(p))) {
      setError("Unsupported file type. Use PDF, DOCX, TXT, or an image.");
      e.target.value = "";
      return;
    }
    setAttachment(f);
    setError(null);
    e.target.value = "";
  };

  const handleSend = () => {
    if (!draft.trim() && !attachment) return;
    if (sendMutation.isPending) return;
    setError(null);
    sendMutation.mutate();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Closed state — floating action button ────────────────────────────────
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label="Open Vantage career assistant"
        className={cn(
          "fixed bottom-6 right-6 z-40",
          "flex items-center gap-2 px-4 h-12 rounded-full",
          "bg-primary text-primary-foreground shadow-lg shadow-primary/30",
          "hover:scale-105 hover:shadow-xl transition-all",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
        )}
      >
        <Sparkles className="h-4 w-4" />
        <span className="text-sm font-medium">Ask Vantage</span>
      </button>
    );
  }

  // ── Open state — chat panel ──────────────────────────────────────────────
  return (
    <div
      className={cn(
        "fixed bottom-6 right-6 z-40",
        "flex flex-col w-[380px] sm:w-[420px] h-[560px] max-h-[80vh]",
        "rounded-2xl border border-border bg-card shadow-2xl shadow-primary/10",
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground leading-none">Vantage</p>
            <p className="text-[11px] text-muted-foreground mt-0.5">Career assistant</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="p-1 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Close Vantage"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {isLoading && messages.length === 0 && (
          <div className="flex items-center justify-center py-10">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoading && messages.length === 0 && (
          <div className="text-center py-8 px-4">
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-3">
              <Sparkles className="h-5 w-5 text-primary" />
            </div>
            <p className="text-sm font-medium text-foreground mb-1">Hi! I&apos;m Vantage.</p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Ask me anything about your career matches — why you got them, what to learn first,
              or attach your CV / a screenshot for deeper feedback.
            </p>
            <div className="mt-4 space-y-1.5">
              {[
                "Why was my top match ranked first?",
                "What should I learn first to close the gaps?",
                "Compare my top 3 careers.",
              ].map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => setDraft(s)}
                  className="block w-full text-xs text-left px-3 py-1.5 rounded-md border border-border hover:border-primary/50 hover:bg-muted/40 text-muted-foreground transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m) => (
          <Bubble key={m.id} message={m} />
        ))}

        {sendMutation.isPending && (
          <div className="flex items-start gap-2">
            <div className="px-3 py-2 rounded-2xl rounded-tl-sm bg-muted text-muted-foreground text-sm flex items-center gap-2">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Thinking…
            </div>
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="border-t border-border p-3">
        {error && (
          <div className="flex items-start gap-2 mb-2 p-2 rounded-md bg-destructive/10 text-destructive text-xs">
            <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {attachment && (
          <div className="flex items-center justify-between gap-2 mb-2 px-2.5 py-1.5 rounded-md bg-muted/50 border border-border text-xs">
            <div className="flex items-center gap-1.5 min-w-0">
              {attachment.type.startsWith("image/") ? (
                <ImageIcon className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              ) : (
                <FileText className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              )}
              <span className="truncate text-foreground">{attachment.name}</span>
              <span className="text-muted-foreground shrink-0">
                ({(attachment.size / 1024).toFixed(0)} KB)
              </span>
            </div>
            <button
              type="button"
              onClick={() => setAttachment(null)}
              className="text-muted-foreground hover:text-foreground"
              aria-label="Remove attachment"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        <div className="flex items-end gap-1.5">
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.png,.jpg,.jpeg,.webp,.gif,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,image/*"
            className="sr-only"
            onChange={handleFile}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted transition-colors shrink-0"
            aria-label="Attach a file"
            disabled={sendMutation.isPending}
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your matches…"
            rows={1}
            className={cn(
              "flex-1 resize-none rounded-md border border-border bg-background px-3 py-2",
              "text-sm placeholder:text-muted-foreground",
              "focus:outline-none focus:ring-2 focus:ring-ring focus:border-transparent",
              "max-h-32 min-h-[36px]",
            )}
            disabled={sendMutation.isPending}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={sendMutation.isPending || (!draft.trim() && !attachment)}
            className={cn(
              "p-2 rounded-md shrink-0 transition-colors",
              "bg-primary text-primary-foreground hover:bg-primary/90",
              "disabled:bg-muted disabled:text-muted-foreground disabled:cursor-not-allowed",
            )}
            aria-label="Send message"
          >
            {sendMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
        <p className="text-[10px] text-muted-foreground/70 mt-1.5 text-center">
          Vantage uses AI — replies are estimates, not career advice.
        </p>
      </div>
    </div>
  );
}

// ── Bubble ────────────────────────────────────────────────────────────────────

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const kind = message.attachment_kind as AttachmentKind | null;

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] px-3 py-2 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap break-words",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-muted text-foreground rounded-tl-sm",
        )}
      >
        {kind && message.attachment_name && (
          <div
            className={cn(
              "flex items-center gap-1.5 mb-1.5 pb-1.5 border-b text-xs font-medium",
              isUser
                ? "border-primary-foreground/20 text-primary-foreground/90"
                : "border-border text-muted-foreground",
            )}
          >
            {kind === "image" ? (
              <ImageIcon className="h-3 w-3" />
            ) : (
              <FileText className="h-3 w-3" />
            )}
            <span className="truncate">{message.attachment_name}</span>
          </div>
        )}
        {message.content}
      </div>
    </div>
  );
}
