"use client";

import * as React from "react";
import { Upload, CheckCircle, XCircle, Loader2 } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import type { ExtractedProfile } from "@/lib/types";
import { cn } from "@/lib/utils";

// ── Error reason → human-readable message ───────────────────────────────────

const REASON_MESSAGES: Record<string, string> = {
  file_too_large:
    "File is too large (max 5 MB). Please compress or trim your resume and try again.",
  unsupported_type:
    "Unsupported file type. Please upload a PDF, DOCX, or plain-text (.txt) file.",
  scanned_pdf:
    "This PDF appears to be scanned with no readable text. " +
    "Upload a text-based PDF or paste your resume as a .txt file.",
  extraction_failed:
    "Couldn't parse your resume after two attempts. You can fill in the form manually.",
  no_resume_keywords:
    "This file doesn't look like a resume. Please check the file or fill in the form manually.",
  low_confidence:
    "Couldn't reliably extract your resume. Please fill in the form manually.",
};

function mapError(err: unknown): string {
  if (err instanceof ApiError) {
    // The backend embeds the reason in the message — just surface it
    return err.message;
  }
  return "Upload failed. Please try again or fill in the form manually.";
}

// ── Types ───────────────────────────────────────────────────────────────────

export interface ResumeUploadWidgetProps {
  /** Called when parsing succeeds — use to prefill form fields. */
  onParsed: (extracted: ExtractedProfile, warnings: string[]) => void;
}

type UploadState = "idle" | "uploading" | "success" | "error";

// ── Component ────────────────────────────────────────────────────────────────

export function ResumeUploadWidget({ onParsed }: ResumeUploadWidgetProps) {
  const [uploadState, setUploadState] = React.useState<UploadState>("idle");
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);
  const [isDragOver, setIsDragOver] = React.useState(false);
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleFile = React.useCallback(
    async (file: File) => {
      // Client-side guard (mirrors backend limit)
      if (file.size > 5 * 1024 * 1024) {
        setErrorMsg(REASON_MESSAGES.file_too_large);
        setUploadState("error");
        return;
      }

      setUploadState("uploading");
      setErrorMsg(null);

      try {
        const result = await api.parseResume(file);
        setUploadState("success");
        onParsed(result.extracted, result.warnings);
      } catch (err) {
        setUploadState("error");
        setErrorMsg(mapError(err));
      }
    },
    [onParsed],
  );

  const onDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    // Reset so the same file can be re-selected after an error
    e.target.value = "";
  };

  // ── Success state ──────────────────────────────────────────────────────────

  if (uploadState === "success") {
    return (
      <div className="flex items-center gap-2.5 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-sm mb-6">
        <CheckCircle className="h-4 w-4 shrink-0" />
        <span className="font-medium flex-1">
          Resume imported — fields pre-filled below. Review and adjust as needed.
        </span>
        <button
          type="button"
          className="text-xs underline text-emerald-600 dark:text-emerald-400 hover:text-emerald-800 dark:hover:text-emerald-200 transition-colors"
          onClick={() => setUploadState("idle")}
        >
          Upload different
        </button>
      </div>
    );
  }

  // ── Drop-zone ──────────────────────────────────────────────────────────────

  return (
    <div className="mb-6 space-y-2">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload resume file"
        className={cn(
          "flex flex-col items-center justify-center gap-2 p-5 rounded-xl border-2 border-dashed",
          "cursor-pointer transition-colors select-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
          isDragOver
            ? "border-primary bg-primary/5"
            : uploadState === "error"
              ? "border-destructive/50 hover:border-destructive/80"
              : "border-border hover:border-primary/50 hover:bg-muted/20",
        )}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={onDrop}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
          className="sr-only"
          onChange={onFileChange}
        />

        {uploadState === "uploading" ? (
          <>
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <p className="text-sm text-muted-foreground">Parsing your resume…</p>
          </>
        ) : (
          <>
            <Upload className="h-6 w-6 text-muted-foreground" />
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">
                Import from resume{" "}
                <span className="font-normal text-muted-foreground">(optional)</span>
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                PDF, DOCX, or TXT · Max 5 MB · Drag &amp; drop or click
              </p>
            </div>
          </>
        )}
      </div>

      {/* Error banner */}
      {uploadState === "error" && errorMsg && (
        <div className="flex items-start gap-2 p-2.5 rounded-lg bg-destructive/10 text-destructive text-xs">
          <XCircle className="h-4 w-4 shrink-0 mt-0.5" />
          <span>{errorMsg}</span>
        </div>
      )}
    </div>
  );
}
