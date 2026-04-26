"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  RefreshCw,
  AlertCircle,
  CheckCircle2,
  XCircle,
  ArrowLeft,
} from "lucide-react";
import Link from "next/link";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { RankedCareer, RoadmapPhase, RuleScores } from "@/lib/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

// ── Confidence ring ───────────────────────────────────────────────────────────

function ConfidenceRing({ value, size = 52 }: { value: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  const offset = circumference * (1 - pct / 100);

  return (
    <div
      className="relative flex items-center justify-center shrink-0"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="rotate-[-90deg]">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="4"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(243 75% 59%)"
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-xs font-bold text-slate-700 tabular-nums">
        {pct}%
      </span>
    </div>
  );
}

// ── Rank badge ────────────────────────────────────────────────────────────────

const RANK_STYLES: Record<number, string> = {
  1: "bg-amber-100 text-amber-700 border-amber-300",
  2: "bg-slate-100 text-slate-600 border-slate-300",
  3: "bg-orange-50 text-orange-600 border-orange-200",
};

function RankBadge({ rank }: { rank: number }) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-bold border shrink-0",
        RANK_STYLES[rank] ?? "bg-slate-50 text-slate-500 border-slate-200",
      )}
    >
      {rank}
    </span>
  );
}

// ── Score breakdown ───────────────────────────────────────────────────────────

function ScoreBreakdown({ scores }: { scores: RuleScores }) {
  const items = [
    {
      label: "Skill fit",
      pct: Math.round((scores.skill / 0.45) * 100),
      color: "bg-indigo-500",
    },
    {
      label: "Personality",
      pct: Math.round((scores.personality / 0.25) * 100),
      color: "bg-violet-500",
    },
    {
      label: "Interests",
      pct: Math.round((scores.interest / 0.15) * 100),
      color: "bg-emerald-500",
    },
  ];

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <span className="text-xs text-slate-500 w-20 shrink-0">{item.label}</span>
          <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all", item.color)}
              style={{ width: `${Math.min(100, item.pct)}%` }}
            />
          </div>
          <span className="text-xs font-medium text-slate-600 w-8 text-right tabular-nums">
            {Math.min(100, item.pct)}%
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Roadmap phase block ───────────────────────────────────────────────────────

const PHASE_STYLES: Record<string, string> = {
  Beginner: "border-emerald-300 bg-emerald-50",
  Intermediate: "border-amber-300 bg-amber-50",
  Advanced: "border-indigo-300 bg-indigo-50",
};

function RoadmapBlock({ phase }: { phase: RoadmapPhase }) {
  return (
    <div
      className={cn(
        "rounded-lg border-2 p-4",
        PHASE_STYLES[phase.phase] ?? "border-slate-200 bg-slate-50",
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-slate-800">{phase.phase}</span>
        <span className="text-xs text-slate-500">{phase.duration_weeks}w</span>
      </div>
      <div className="space-y-2.5">
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
            Skills
          </p>
          <div className="flex flex-wrap gap-1">
            {phase.skills.map((s) => (
              <span
                key={s}
                className="px-2 py-0.5 text-xs rounded-full bg-white border border-slate-200 text-slate-600"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1">
            Projects
          </p>
          <ul className="space-y-1">
            {phase.projects.map((p) => (
              <li key={p} className="flex gap-1.5 text-xs text-slate-600">
                <span className="text-slate-400 shrink-0 mt-0.5">→</span>
                {p}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ── Career card ───────────────────────────────────────────────────────────────

function CareerCard({
  career,
  rank,
  defaultOpen = false,
}: {
  career: RankedCareer;
  rank: number;
  defaultOpen?: boolean;
}) {
  return (
    <div
      className={cn(
        "bg-white rounded-2xl border shadow-sm overflow-hidden",
        rank === 1 ? "border-primary/40" : "border-slate-200",
      )}
    >
      {rank === 1 && (
        <div className="bg-primary/5 border-b border-primary/20 px-5 py-2">
          <span className="text-xs font-semibold text-primary tracking-widest">
            BEST MATCH
          </span>
        </div>
      )}

      <div className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5 min-w-0">
            <RankBadge rank={rank} />
            <div className="min-w-0">
              <h2
                className={cn(
                  "font-bold text-slate-900 leading-tight",
                  rank === 1 ? "text-xl" : "text-base",
                )}
              >
                {career.name}
              </h2>
              <span className="text-xs text-slate-500">{career.category}</span>
            </div>
          </div>
          <ConfidenceRing
            value={career.confidence}
            size={rank === 1 ? 64 : 52}
          />
        </div>

        {/* Fit reasoning preview */}
        <p
          className={cn(
            "mt-3 text-sm text-slate-600 leading-relaxed",
            rank !== 1 && "line-clamp-2",
          )}
        >
          {career.fit_reasoning}
        </p>

        {/* Expandable details */}
        <Accordion
          type="single"
          collapsible
          defaultValue={defaultOpen ? "details" : undefined}
          className="mt-3"
        >
          <AccordionItem value="details" className="border-t border-slate-100">
            <AccordionTrigger className="text-sm text-slate-500 py-3 hover:no-underline hover:text-primary">
              Full analysis
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-6 pt-1">
                {/* Strengths & Risks */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                      Strengths
                    </p>
                    <ul className="space-y-1.5">
                      {career.strengths.map((s) => (
                        <li key={s} className="flex gap-2 text-sm text-slate-700">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                          {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                      Risks
                    </p>
                    <ul className="space-y-1.5">
                      {career.risks.map((r) => (
                        <li key={r} className="flex gap-2 text-sm text-slate-700">
                          <XCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Skill gaps */}
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
                    Skill gaps
                  </p>
                  {career.skill_gaps.length === 0 ? (
                    <p className="text-sm text-emerald-600 font-medium">
                      No skill gaps — you&apos;re a strong match!
                    </p>
                  ) : (
                    <div className="rounded-lg border border-slate-200 overflow-hidden divide-y divide-slate-100">
                      {career.skill_gaps.map((g) => (
                        <div
                          key={g.skill}
                          className="flex items-center justify-between px-3 py-2"
                        >
                          <span className="text-sm text-slate-700">{g.skill}</span>
                          <Badge variant={g.difficulty}>{g.difficulty}</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Score breakdown */}
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    Score breakdown
                  </p>
                  <ScoreBreakdown scores={career.rule_scores} />
                </div>

                {/* Roadmap */}
                <div>
                  <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
                    Learning roadmap
                  </p>
                  <div className="grid sm:grid-cols-3 gap-3">
                    {career.roadmap.map((phase) => (
                      <RoadmapBlock key={phase.phase} phase={phase} />
                    ))}
                  </div>
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function ResultsSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-52 w-full rounded-2xl" />
      <div className="grid sm:grid-cols-2 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-36 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ResultsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [rerunning, setRerunning] = React.useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["recommendation", id],
    queryFn: () => api.getRecommendation(id),
  });

  const handleRerun = async () => {
    if (!data || rerunning) return;
    setRerunning(true);
    try {
      const fresh = await api.createRecommendation(data.profile_id, true);
      router.push(`/results/${fresh.id}`);
    } catch {
      setRerunning(false);
    }
  };

  const careers = data?.result.ranked_careers ?? [];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Sticky header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/profile"
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            New profile
          </Link>
          <span className="text-sm font-semibold text-slate-700 tracking-tight">
            Echelon
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRerun}
            disabled={!data || rerunning}
            className="gap-1.5 text-slate-600"
          >
            <RefreshCw
              className={cn("h-3.5 w-3.5", rerunning && "animate-spin")}
            />
            Re-run
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-900">
            Your career matches
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Ranked by AI fit analysis across your skills, personality, and
            interests.
          </p>
        </div>

        {isLoading && <ResultsSkeleton />}

        {isError && (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="font-semibold text-slate-800">Failed to load results</p>
            <p className="text-sm text-slate-500">
              {error instanceof Error ? error.message : "Unknown error"}
            </p>
            <Button
              variant="outline"
              className="mt-2"
              onClick={() => router.push("/profile")}
            >
              Start over
            </Button>
          </div>
        )}

        {data && careers.length > 0 && (
          <div className="space-y-4">
            {/* Top match — full width, accordion open by default */}
            <CareerCard career={careers[0]} rank={1} defaultOpen />

            {/* Remaining matches — 2-column grid */}
            {careers.length > 1 && (
              <div className="grid sm:grid-cols-2 gap-4">
                {careers.slice(1).map((career, i) => (
                  <CareerCard key={career.slug} career={career} rank={i + 2} />
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
