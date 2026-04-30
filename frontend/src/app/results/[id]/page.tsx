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
  ExternalLink,
  Sparkles,
  Info,
  BookOpen,
  Youtube,
  Globe,
  Share2,
  Check,
  Download,
} from "lucide-react";
import Link from "next/link";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  CareerSource,
  Course,
  CourseProvider,
  ProposedCareer,
  RankedCareer,
  RoadmapPhase,
  RuleScores,
} from "@/lib/types";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ThemeToggle } from "@/components/theme-toggle";
import { Vantage } from "@/components/Vantage";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

// ── Source badge ──────────────────────────────────────────────────────────────

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
        {/* Track — uses CSS var so it responds to dark mode */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="var(--ring-track)"
          strokeWidth="4"
        />
        {/* Fill — indigo primary */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="4"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
        />
      </svg>
      <span className="absolute text-xs font-bold text-foreground tabular-nums">
        {pct}%
      </span>
    </div>
  );
}

// ── Rank badge ────────────────────────────────────────────────────────────────

const RANK_STYLES: Record<number, string> = {
  1: "bg-amber-100 text-amber-700 border-amber-300 dark:bg-amber-900 dark:text-amber-300 dark:border-amber-700",
  2: "bg-muted text-muted-foreground border-border",
  3: "bg-orange-50 text-orange-600 border-orange-200 dark:bg-orange-950 dark:text-orange-400 dark:border-orange-800",
};

function RankBadge({ rank }: { rank: number }) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center h-6 w-6 rounded-full text-xs font-bold border shrink-0",
        RANK_STYLES[rank] ?? "bg-muted/50 text-muted-foreground border-border",
      )}
    >
      {rank}
    </span>
  );
}

// ── Score breakdown ───────────────────────────────────────────────────────────

function ScoreBreakdown({ scores, confidence }: { scores: RuleScores; confidence: number }) {
  const items = [
    { label: "Skill fit",     pct: Math.round((scores.skill        / 0.45) * 100), color: "bg-indigo-500",  weight: "45%" },
    { label: "Opt. skills",   pct: Math.round((scores.optional     / 0.15) * 100), color: "bg-blue-400",    weight: "15%" },
    { label: "Personality",   pct: Math.round((scores.personality  / 0.25) * 100), color: "bg-violet-500",  weight: "25%" },
    { label: "Interests",     pct: Math.round((scores.interest     / 0.15) * 100), color: "bg-emerald-500", weight: "15%" },
  ];
  const totalPct = Math.round(scores.total * 100);

  return (
    <div className="space-y-3">
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.label} className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground w-20 shrink-0">{item.label}</span>
            <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
              <div
                className={cn("h-full rounded-full transition-all", item.color)}
                style={{ width: `${Math.min(100, item.pct)}%` }}
              />
            </div>
            <span className="text-xs font-medium text-muted-foreground w-8 text-right tabular-nums">
              {Math.min(100, item.pct)}%
            </span>
          </div>
        ))}
      </div>

      {/* Summary row */}
      <div className="flex items-center justify-between pt-2 border-t border-border">
        <span className="text-xs text-muted-foreground">
          Rule score{" "}
          <span
            className="cursor-help underline decoration-dotted"
            title="Weighted sum: skill×0.45 + optional×0.15 + personality×0.25 + interests×0.15"
          >
            {totalPct}%
          </span>
          {" · "}
          AI confidence{" "}
          <span
            className="cursor-help underline decoration-dotted"
            title="LLM re-ranking score — how strongly the model believes this career fits your profile. Independent of the rule score."
          >
            {Math.round(confidence)}%
          </span>
        </span>
        <span className="text-[10px] text-muted-foreground/60 italic">
          scores are approximations
        </span>
      </div>
    </div>
  );
}

// ── Roadmap phase block ───────────────────────────────────────────────────────

const PHASE_STYLES: Record<string, string> = {
  Beginner:
    "border-emerald-300 bg-emerald-50 dark:border-emerald-800 dark:bg-emerald-950",
  Intermediate:
    "border-amber-300 bg-amber-50 dark:border-amber-800 dark:bg-amber-950",
  Advanced:
    "border-indigo-300 bg-indigo-50 dark:border-indigo-800 dark:bg-indigo-950",
};

function RoadmapBlock({ phase }: { phase: RoadmapPhase }) {
  return (
    <div
      className={cn(
        "rounded-lg border-2 p-4",
        PHASE_STYLES[phase.phase] ?? "border-border bg-muted",
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-semibold text-foreground">{phase.phase}</span>
        <span className="text-xs text-muted-foreground">{phase.duration_weeks}w</span>
      </div>
      <div className="space-y-2.5">
        <div>
          <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-1">
            Skills
          </p>
          <div className="flex flex-wrap gap-1">
            {phase.skills.map((s) => (
              <span
                key={s}
                className="px-2 py-0.5 text-xs rounded-full bg-card border border-border text-muted-foreground user-content"
              >
                {s}
              </span>
            ))}
          </div>
        </div>
        <div>
          <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-1">
            Projects
          </p>
          <ul className="space-y-1">
            {phase.projects.map((p) => (
              <li key={p} className="flex gap-1.5 text-xs text-muted-foreground">
                <span className="text-muted-foreground/50 shrink-0 mt-0.5">→</span>
                <span className="user-content min-w-0">{p}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

// ── Course card ───────────────────────────────────────────────────────────────

const PROVIDER_ICON: Record<CourseProvider, React.ReactNode> = {
  youtube: <Youtube className="h-3 w-3" />,
  tavily: <Globe className="h-3 w-3" />,
};

const PROVIDER_LABEL: Record<CourseProvider, string> = {
  youtube: "YouTube",
  tavily: "Web",
};

const PROVIDER_STYLES: Record<CourseProvider, string> = {
  youtube: "bg-rose-50 text-rose-600 border-rose-200 dark:bg-rose-950 dark:text-rose-400 dark:border-rose-800",
  tavily: "bg-sky-50 text-sky-600 border-sky-200 dark:bg-sky-950 dark:text-sky-400 dark:border-sky-800",
};

function CourseCard({ course }: { course: Course }) {
  return (
    <a
      href={course.url}
      target="_blank"
      rel="noopener noreferrer"
      className="group flex gap-3 p-3 rounded-xl border border-border hover:border-primary/40 hover:bg-muted/30 transition-colors"
    >
      {course.thumbnail ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={course.thumbnail}
          alt=""
          className="w-20 h-14 object-cover rounded-lg shrink-0 bg-muted"
        />
      ) : (
        <div className="w-20 h-14 rounded-lg bg-muted shrink-0 flex items-center justify-center">
          <BookOpen className="h-5 w-5 text-muted-foreground/50" />
        </div>
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-medium text-foreground leading-snug line-clamp-2 group-hover:text-primary transition-colors">
            {course.title}
          </p>
          <ExternalLink className="h-3.5 w-3.5 text-muted-foreground shrink-0 mt-0.5" />
        </div>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <span
            className={cn(
              "inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border",
              PROVIDER_STYLES[course.provider],
            )}
          >
            {PROVIDER_ICON[course.provider]}
            {PROVIDER_LABEL[course.provider]}
          </span>
          <span className="text-xs text-muted-foreground truncate">{course.channel}</span>
          <span className="text-xs text-muted-foreground ml-auto tabular-nums shrink-0">
            {Math.round(course.relevance_score * 100)}% match
          </span>
        </div>
        <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{course.rationale}</p>
      </div>
    </a>
  );
}

// ── Bridge the gap section (lazy-loaded inside accordion) ─────────────────────

function BridgeTheGap({
  careerSlug,
  careerName,
  gapSkills,
}: {
  careerSlug: string;
  careerName: string;
  gapSkills: string[];
}) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ["courses", careerSlug],
    queryFn: () => api.getCourses(careerSlug, careerName, gapSkills),
    staleTime: 5 * 60 * 1000,
  });

  const courses = data?.courses ?? [];

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide">
          Bridge the gap
        </p>
        {data && (
          <span
            className="text-[10px] text-muted-foreground cursor-help"
            title={data.source_note}
          >
            <Info className="h-3 w-3 inline mr-0.5" />
            About these courses
          </span>
        )}
      </div>

      {isLoading && (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-xl bg-muted animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-xs text-muted-foreground italic">
          Couldn&apos;t load course recommendations right now.
        </p>
      )}

      {!isLoading && !isError && courses.length === 0 && (
        <p className="text-xs text-muted-foreground italic">
          No course recommendations available — add a YouTube or Tavily API key to enable this feature.
        </p>
      )}

      {courses.length > 0 && (
        <div className="space-y-2">
          {courses.map((course) => (
            <CourseCard key={course.url} course={course} />
          ))}
        </div>
      )}
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
  const [accordionValue, setAccordionValue] = React.useState<string>(
    defaultOpen ? "details" : "",
  );
  const isOpen = accordionValue === "details";

  return (
    <div
      className={cn(
        "bg-card rounded-2xl border shadow-sm overflow-hidden",
        rank === 1 ? "border-primary/40" : "border-border",
      )}
    >
      {rank === 1 && (
        <div className="bg-primary/10 border-b border-primary/20 px-5 py-2">
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
              <div className="flex items-center gap-2 flex-wrap">
                <h2
                  className={cn(
                    "font-bold text-foreground leading-tight break-words min-w-0",
                    rank === 1 ? "text-xl" : "text-base",
                  )}
                >
                  {career.name}
                </h2>
                {career.source && <SourceBadge source={career.source} />}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs text-muted-foreground">{career.category}</span>
                {career.external_url && (
                  <a
                    href={career.external_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-0.5 text-xs text-blue-500 hover:text-blue-400 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
                  >
                    View on O*NET
                    <ExternalLink className="h-3 w-3" />
                  </a>
                )}
              </div>
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
            "mt-3 text-sm text-muted-foreground leading-relaxed user-content",
            rank !== 1 && "line-clamp-2",
          )}
        >
          {career.fit_reasoning}
        </p>

        {/* Expandable details */}
        <Accordion
          type="single"
          collapsible
          value={accordionValue}
          onValueChange={setAccordionValue}
          className="mt-3"
        >
          <AccordionItem value="details" className="border-t border-border">
            <AccordionTrigger className="text-sm text-muted-foreground py-3 hover:no-underline hover:text-primary">
              Full analysis
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-6 pt-1">
                {/* Strengths & Risks */}
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-2">
                      Strengths
                    </p>
                    <ul className="space-y-1.5">
                      {career.strengths.map((s) => (
                        <li key={s} className="flex gap-2 text-sm text-foreground">
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                          <span className="user-content min-w-0">{s}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-2">
                      Risks
                    </p>
                    <ul className="space-y-1.5">
                      {career.risks.map((r) => (
                        <li key={r} className="flex gap-2 text-sm text-foreground">
                          <XCircle className="h-4 w-4 text-rose-400 shrink-0 mt-0.5" />
                          <span className="user-content min-w-0">{r}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                {/* Skill gaps */}
                <div>
                  <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-2">
                    Skill gaps
                  </p>
                  {career.skill_gaps.length === 0 ? (
                    <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                      No skill gaps — you&apos;re a strong match!
                    </p>
                  ) : (
                    <div className="rounded-lg border border-border overflow-hidden divide-y divide-border">
                      {career.skill_gaps.map((g) => (
                        <div
                          key={g.skill}
                          className="flex items-center justify-between px-3 py-2"
                        >
                          <span className="text-sm text-foreground user-content">{g.skill}</span>
                          <Badge variant={g.difficulty}>{g.difficulty}</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Score breakdown */}
                <div>
                  <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-3">
                    How we scored this
                  </p>
                  <ScoreBreakdown scores={career.rule_scores} confidence={career.confidence} />
                </div>

                {/* Roadmap */}
                <div>
                  <p className="text-xs font-semibold text-muted-foreground/60 uppercase tracking-wide mb-3">
                    Learning roadmap
                  </p>
                  <div className="grid sm:grid-cols-3 gap-3">
                    {career.roadmap.map((phase) => (
                      <RoadmapBlock key={phase.phase} phase={phase} />
                    ))}
                  </div>
                </div>

                {/* Course recommendations — only fetched once accordion opens */}
                {isOpen && (
                  <BridgeTheGap
                    careerSlug={career.slug}
                    careerName={career.name}
                    gapSkills={career.skill_gaps.map((g) => g.skill)}
                  />
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </div>
    </div>
  );
}

// ── Proposed career card ──────────────────────────────────────────────────────

function ProposedCareerCard({ career }: { career: ProposedCareer }) {
  return (
    <div className="bg-card rounded-xl border border-amber-200 dark:border-amber-800 shadow-sm p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-base font-bold text-foreground leading-tight break-words min-w-0">
              {career.name}
            </h3>
            <SourceBadge source="llm_proposed" />
          </div>
          <span className="text-xs text-muted-foreground">{career.category}</span>
        </div>
      </div>
      <p className="mt-2 text-sm text-muted-foreground leading-relaxed user-content">
        {career.description}
      </p>
      {career.rationale && (
        <p className="mt-2 text-xs text-amber-700 dark:text-amber-400 italic border-t border-amber-100 dark:border-amber-800 pt-2 user-content">
          {career.rationale}
        </p>
      )}
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
  const [sharing, setSharing] = React.useState(false);
  const [shared, setShared] = React.useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["recommendation", id],
    queryFn: () => api.getRecommendation(id),
  });

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
  const pdfHref = data ? `${apiBase}/recommendations/${data.id}/pdf` : "#";

  const handleShare = async () => {
    if (!data || sharing) return;
    setSharing(true);
    try {
      await api.shareRecommendation(id);
      const shareUrl = `${window.location.origin}/r/${id}`;
      await navigator.clipboard.writeText(shareUrl);
      setShared(true);
      setTimeout(() => setShared(false), 3000);
    } catch {
      // clipboard may be denied — still mark public but don't show checkmark
    } finally {
      setSharing(false);
    }
  };

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
  const proposed = data?.result.proposed_careers ?? [];

  return (
    <div className="min-h-screen bg-background">
      {/* Sticky header */}
      <header className="bg-card border-b border-border sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/profile"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            New profile
          </Link>
          <span className="text-sm font-semibold text-foreground tracking-tight">
            Echelon
          </span>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <Button
              variant="outline"
              size="sm"
              asChild
              disabled={!data}
              className="gap-1.5"
            >
              <a href={pdfHref} download>
                <Download className="h-3.5 w-3.5" />
                PDF
              </a>
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleShare}
              disabled={!data || sharing}
              className="gap-1.5"
              title="Copy shareable link to clipboard"
            >
              {shared ? (
                <Check className="h-3.5 w-3.5 text-emerald-500" />
              ) : (
                <Share2 className="h-3.5 w-3.5" />
              )}
              {shared ? "Copied!" : "Share"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRerun}
              disabled={!data || rerunning}
              className="gap-1.5"
            >
              <RefreshCw
                className={cn("h-3.5 w-3.5", rerunning && "animate-spin")}
              />
              Re-run
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-foreground">
            Your career matches
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Ranked by AI fit analysis across your skills, personality, and
            interests.
          </p>
        </div>

        {isLoading && <ResultsSkeleton />}

        {isError && (
          <div className="flex flex-col items-center justify-center py-20 gap-3 text-center">
            <AlertCircle className="h-8 w-8 text-destructive" />
            <p className="font-semibold text-foreground">Failed to load results</p>
            <p className="text-sm text-muted-foreground">
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

            {/* AI-proposed careers */}
            {proposed.length > 0 && (
              <section className="mt-8">
                <div className="flex items-center gap-2 mb-3">
                  <Sparkles className="h-4 w-4 text-amber-500" />
                  <h2 className="text-sm font-semibold text-foreground">
                    AI-Generated Suggestions
                  </h2>
                  <span
                    className="inline-flex items-center gap-1 text-xs text-muted-foreground cursor-help"
                    title="These careers were invented by the AI because your profile didn't closely match existing options. They may not yet exist as established roles — treat them as inspiration."
                  >
                    <Info className="h-3.5 w-3.5" />
                    Experimental
                  </span>
                </div>
                <div className="rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/30 p-3 mb-3">
                  <p className="text-xs text-amber-700 dark:text-amber-400 leading-relaxed">
                    Your profile didn&apos;t closely match our career database, so our AI
                    generated these suggestions based on your unique combination of
                    skills and interests. These are not verified roles — they&apos;re
                    creative possibilities to explore.
                  </p>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {proposed.map((career) => (
                    <ProposedCareerCard key={career.slug} career={career} />
                  ))}
                </div>
              </section>
            )}
          </div>
        )}
      </main>

      {/* Vantage chatbot — only mount when we have a recommendation id */}
      {data && <Vantage recommendationId={data.id} />}
    </div>
  );
}
