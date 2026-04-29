"use client";

import * as React from "react";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  XCircle,
  Sparkles,
  Info,
} from "lucide-react";
import Link from "next/link";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  CareerSource,
  ProposedCareer,
  RankedCareer,
  RoadmapPhase,
  RuleScores,
} from "@/lib/types";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

// ── Re-used display helpers (duplicated from results page to keep the public
//    page fully self-contained and independent of internal layout changes) ────

const SOURCE_LABEL: Record<CareerSource, string> = {
  onet: "O*NET",
  manual: "Curated",
  llm_proposed: "AI Suggested",
};

const SOURCE_STYLES: Record<CareerSource, string> = {
  onet: "bg-blue-50 text-blue-600 border-blue-200 dark:bg-blue-950 dark:text-blue-400 dark:border-blue-800",
  manual: "bg-muted text-muted-foreground border-border",
  llm_proposed:
    "bg-amber-50 text-amber-600 border-amber-200 dark:bg-amber-950 dark:text-amber-400 dark:border-amber-800",
};

function SourceBadge({ source }: { source: CareerSource }) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border tracking-wide",
        SOURCE_STYLES[source],
      )}
    >
      {SOURCE_LABEL[source]}
    </span>
  );
}

function ConfidenceRing({ value, size = 52 }: { value: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = Math.min(100, Math.max(0, Math.round(value)));
  const offset = circumference * (1 - pct / 100);

  return (
    <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="rotate-[-90deg]">
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--ring-track)" strokeWidth="4" />
        <circle
          cx={size / 2} cy={size / 2} r={radius} fill="none"
          stroke="hsl(var(--primary))" strokeWidth="4"
          strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-xs font-bold text-foreground tabular-nums">{pct}%</span>
    </div>
  );
}

function ScoreBreakdown({ scores, confidence }: { scores: RuleScores; confidence: number }) {
  const items = [
    { label: "Skill fit",    pct: Math.round((scores.skill       / 0.45) * 100), color: "bg-indigo-500"  },
    { label: "Opt. skills",  pct: Math.round((scores.optional    / 0.15) * 100), color: "bg-blue-400"    },
    { label: "Personality",  pct: Math.round((scores.personality / 0.25) * 100), color: "bg-violet-500"  },
    { label: "Interests",    pct: Math.round((scores.interest    / 0.15) * 100), color: "bg-emerald-500" },
  ];
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground w-20 shrink-0">{item.label}</span>
          <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
            <div className={cn("h-full rounded-full", item.color)} style={{ width: `${Math.min(100, item.pct)}%` }} />
          </div>
          <span className="text-xs font-medium text-muted-foreground w-8 text-right tabular-nums">
            {Math.min(100, item.pct)}%
          </span>
        </div>
      ))}
      <div className="flex items-center justify-between pt-1.5 border-t border-border">
        <span className="text-xs text-muted-foreground">
          Rule score {Math.round(scores.total * 100)}% · AI confidence {Math.round(confidence)}%
        </span>
        <span className="text-[10px] text-muted-foreground/60 italic">approx.</span>
      </div>
    </div>
  );
}

const PHASE_STYLES: Record<string, string> = {
  Beginner: "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950",
  Intermediate: "border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950",
  Advanced: "border-indigo-300 bg-indigo-50 dark:border-indigo-800 dark:bg-indigo-950",
};

function RoadmapBlock({ phase }: { phase: RoadmapPhase }) {
  return (
    <div className={cn("rounded-lg border-2 p-4", PHASE_STYLES[phase.phase] ?? "border-border bg-muted")}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-foreground">{phase.phase}</span>
        <span className="text-xs text-muted-foreground">{phase.duration_weeks}w</span>
      </div>
      <div className="space-y-2.5">
        <div>
          <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-1">Skills</p>
          <div className="flex flex-wrap gap-1">
            {phase.skills.map((s) => (
              <span key={s} className="px-2 py-0.5 text-xs rounded-full bg-card border border-border text-muted-foreground">{s}</span>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-1">Projects</p>
          <ul className="space-y-1">
            {phase.projects.map((p) => (
              <li key={p} className="flex gap-1.5 text-xs text-muted-foreground">
                <span className="text-muted-foreground/50 shrink-0 mt-0.5">→</span>
                <span className="min-w-0">{p}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function SharedCareerCard({ career, rank }: { career: RankedCareer; rank: number }) {
  const RANK_STYLES: Record<number, string> = {
    1: "bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-900 dark:text-amber-300 dark:border-amber-700",
    2: "bg-muted text-muted-foreground border-border",
    3: "bg-orange-50 text-orange-600 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-800",
  };

  return (
    <div className={cn("bg-card rounded-2xl border shadow-sm overflow-hidden", rank === 1 ? "border-primary/40" : "border-border")}>
      {rank === 1 && (
        <div className="bg-primary/10 border-b border-primary/20 px-5 py-2">
          <span className="text-xs font-semibold text-primary tracking-widest">BEST MATCH</span>
        </div>
      )}
      <div className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-2.5 min-w-0">
            <span className={cn("inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-bold border shrink-0", RANK_STYLES[rank] ?? "bg-muted/50 text-muted-foreground border-border")}>
              {rank}
            </span>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className={cn("font-bold text-foreground leading-tight break-words min-w-0", rank === 1 ? "text-xl" : "text-base")}>
                  {career.name}
                </h2>
                {career.source && <SourceBadge source={career.source} />}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-muted-foreground">{career.category}</span>
                {career.external_url && (
                  <a href={career.external_url} target="_blank" rel="noopener noreferrer"
                    className="inline-flex items-center gap-0.5 text-xs text-blue-500 hover:text-blue-400 dark:text-blue-400 dark:hover:text-blue-300 transition-colors">
                    View on O*NET <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
            </div>
          </div>
          <ConfidenceRing value={career.confidence} size={rank === 1 ? 64 : 52} />
        </div>

        <p className={cn("mt-3 text-sm text-muted-foreground leading-relaxed", rank !== 1 && "line-clamp-2")}>
          {career.fit_reasoning}
        </p>

        <Accordion type="single" collapsible className="mt-3">
          <AccordionItem value="details" className="border-t border-border">
            <AccordionTrigger className="text-sm text-muted-foreground py-3 hover:no-underline hover:text-primary">
              Full analysis
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-6 pt-1">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-2">Strengths</p>
                    <ul className="space-y-1.5">
                      {career.strengths.map((s) => (
                        <li key={s} className="flex gap-2 text-sm text-foreground">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                          <span className="min-w-0">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-2">Risks</p>
                    <ul className="space-y-1.5">
                      {career.risks.map((r) => (
                        <li key={r} className="flex gap-2 text-sm text-foreground">
                          <XCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                          <span className="min-w-0">{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-2">Skill gaps</p>
                  {career.skill_gaps.length === 0 ? (
                    <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">No skill gaps — you&apos;re a strong match!</p>
                  ) : (
                    <div className="rounded-lg border border-border overflow-hidden divide-y divide-border">
                      {career.skill_gaps.map((g) => (
                        <div key={g.skill} className="flex items-center justify-between px-3 py-2">
                          <span className="text-sm text-foreground">{g.skill}</span>
                          <Badge variant={g.difficulty}>{g.difficulty}</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-3">Score breakdown</p>
                  <ScoreBreakdown scores={career.rule_scores} confidence={career.confidence} />
                </div>

                <div>
                  <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-3">Learning roadmap</p>
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PublicSharePage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["public-recommendation", id],
    queryFn: () => api.getPublicRecommendation(id),
  });

  const careers = data?.result.ranked_careers ?? [];
  const proposed = data?.result.proposed_careers ?? [];

  return (
    <div className="min-h-screen bg-background">
      <header className="bg-card border-b border-border">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <span className="text-sm font-semibold text-foreground tracking-tight">Echelon</span>
          <Link
            href="/profile"
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            Try it yourself →
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-foreground">Shared career matches</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Someone shared their Echelon career analysis with you.{" "}
            <Link href="/profile" className="text-primary hover:underline">
              Run your own analysis →
            </Link>
          </p>
        </div>

        {isLoading && (
          <div className="space-y-4">
            <Skeleton className="h-52 w-full rounded-2xl" />
            <div className="grid sm:grid-cols-2 gap-4">
              {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-36 rounded-2xl" />)}
            </div>
          </div>
        )}

        {isError && (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="font-semibold text-foreground">This link is no longer available</p>
            <p className="text-sm text-muted-foreground">
              The share link may have expired or been removed.
            </p>
            <Link href="/profile" className="text-sm text-primary hover:underline mt-2">
              Run your own analysis →
            </Link>
          </div>
        )}

        {data && careers.length > 0 && (
          <div className="space-y-4">
            <SharedCareerCard career={careers[0]} rank={1} />
            {careers.length > 1 && (
              <div className="grid sm:grid-cols-2 gap-4">
                {careers.slice(1).map((career, i) => (
                  <SharedCareerCard key={career.slug} career={career} rank={i + 2} />
                ))}
              </div>
            )}

            {proposed.length > 0 && (
              <section className="mt-8">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  <h2 className="text-sm font-semibold text-foreground">AI-Generated Suggestions</h2>
                  <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                    <Info className="h-3.5 w-3.5" />
                    Experimental
                  </span>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {proposed.map((career: ProposedCareer) => (
                    <div key={career.slug} className="bg-card rounded-xl border border-amber-200 dark:border-amber-800 shadow-sm p-4">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <h3 className="text-base font-bold text-foreground break-words min-w-0">{career.name}</h3>
                        <SourceBadge source="llm_proposed" />
                      </div>
                      <span className="text-xs text-muted-foreground">{career.category}</span>
                      <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{career.description}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            <p className="text-xs text-muted-foreground text-center pt-4 border-t border-border">
              AI-generated career analysis. Confidence scores are estimates, not guarantees.
              Echelon is a portfolio project — not career advice.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
