"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle, Loader2, X } from "lucide-react";

import { profileSchema, type ProfileFormValues } from "@/lib/schemas";
import { SKILL_OPTIONS } from "@/lib/skills";
import { api, ApiError } from "@/lib/api";
import type { ExtractedProfile } from "@/lib/types";
import { cn } from "@/lib/utils";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { TagInput } from "@/components/TagInput";
import { ResumeUploadWidget } from "@/components/ResumeUploadWidget";
import { OnboardingTour } from "@/components/OnboardingTour";

const STEPS = ["Skills", "Interests", "Education", "Personality"] as const;

const EDUCATION_OPTIONS = [
  { value: "high_school", label: "High School" },
  { value: "diploma", label: "Diploma / Associate's" },
  { value: "bachelors", label: "Bachelor's Degree" },
  { value: "masters", label: "Master's Degree" },
  { value: "phd", label: "Doctorate / PhD" },
] as const;

const PERSONALITY_TRAITS = [
  {
    key: "openness" as const,
    label: "Openness to new experiences",
    low: "Prefer routine",
    high: "Love exploring new ideas",
  },
  {
    key: "conscientiousness" as const,
    label: "Organization & attention to detail",
    low: "Flexible & spontaneous",
    high: "Highly organized",
  },
  {
    key: "extraversion" as const,
    label: "Energy from social interaction",
    low: "Prefer working alone",
    high: "Thrive in teams",
  },
  {
    key: "agreeableness" as const,
    label: "Cooperation & empathy",
    low: "Direct & competitive",
    high: "Collaborative & empathetic",
  },
  {
    key: "neuroticism" as const,
    label: "Emotional sensitivity",
    low: "Calm under pressure",
    high: "Highly emotionally aware",
  },
] as const;

const INTEREST_SUGGESTIONS = [
  "Technology",
  "Artificial Intelligence",
  "Web Development",
  "Mobile Apps",
  "Data Science",
  "Cybersecurity",
  "Cloud Computing",
  "Open Source",
  "Design",
  "Product Management",
  "Business",
  "Finance",
  "Healthcare",
  "Education",
  "Gaming",
  "Research",
  "Startups",
  "Sustainability",
  "Blockchain",
  "DevOps",
  "Machine Learning",
];

const STEP_FIELDS: Record<number, Array<keyof ProfileFormValues>> = {
  0: ["skills"],
  1: ["interests"],
  2: ["education_level"],
  3: ["personality"],
};

export default function ProfilePage() {
  const router = useRouter();
  const [step, setStep] = React.useState(0);
  const [submitting, setSubmitting] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [parseWarnings, setParseWarnings] = React.useState<string[]>([]);

  const {
    control,
    handleSubmit,
    trigger,
    setValue,
    formState: { errors },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      skills: [],
      interests: [],
      education_level: "bachelors",
      personality: {
        openness: 50,
        conscientiousness: 50,
        extraversion: 50,
        agreeableness: 50,
        neuroticism: 50,
      },
      constraints: null,
    },
  });

  /** Called when the resume widget successfully parses a file. */
  const onResumeParsed = (extracted: ExtractedProfile, warnings: string[]) => {
    if (extracted.skills.length > 0) {
      setValue("skills", extracted.skills, { shouldValidate: true });
    }
    if (extracted.interests.length > 0) {
      setValue("interests", extracted.interests, { shouldValidate: true });
    }
    if (extracted.education_level) {
      setValue("education_level", extracted.education_level, { shouldValidate: true });
    }
    setParseWarnings(warnings);
    // Jump to Skills step so user can review pre-filled data
    setStep(0);
  };

  const next = async () => {
    const valid = await trigger(STEP_FIELDS[step]);
    if (valid) setStep((s) => s + 1);
  };

  const back = () => setStep((s) => s - 1);

  const onSubmit = async (data: ProfileFormValues) => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      const profile = await api.createProfile(data);
      const recommendation = await api.createRecommendation(profile.id);
      router.push(`/results/${recommendation.id}`);
    } catch (err) {
      setSubmitError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong. Please try again.",
      );
      setSubmitting(false);
    }
  };

  if (submitting) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-center px-4 bg-background">
        <Loader2 className="h-10 w-10 animate-spin text-primary" />
        <p className="text-lg font-semibold text-foreground">
          Analyzing your profile with AI…
        </p>
        <p className="text-sm text-muted-foreground">
          This usually takes 10–20 seconds.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center py-12 px-4">
      <div className="w-full max-w-xl">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-foreground">
            Build your profile
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            We&apos;ll use this to match you with career paths that fit.
          </p>
        </div>

        <OnboardingTour />

        {/* Resume upload */}
        <div id="tour-resume">
          <ResumeUploadWidget onParsed={onResumeParsed} />
        </div>

        {/* Parse warnings */}
        {parseWarnings.length > 0 && (
          <div className="mb-6 p-3 rounded-xl border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950 space-y-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-300 text-xs font-semibold">
                <AlertTriangle className="h-3.5 w-3.5" />
                Some fields couldn&apos;t be filled automatically:
              </div>
              <button
                type="button"
                onClick={() => setParseWarnings([])}
                className="text-amber-500 hover:text-amber-700 dark:hover:text-amber-200"
                aria-label="Dismiss warnings"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
            <ul className="list-disc list-inside space-y-0.5">
              {parseWarnings.map((w, i) => (
                <li key={i} className="text-xs text-amber-600 dark:text-amber-400">
                  {w}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Step indicator */}
        <div id="tour-steps" className="flex items-center justify-between mb-8">
          {STEPS.map((label, i) => (
            <React.Fragment key={label}>
              <div className="flex flex-col items-center gap-1">
                <div
                  className={cn(
                    "h-8 w-8 rounded-full flex items-center justify-center text-sm font-semibold border-2 transition-colors",
                    i < step
                      ? "bg-primary border-primary text-primary-foreground"
                      : i === step
                        ? "border-primary text-primary bg-card"
                        : "border-border text-muted-foreground bg-card",
                  )}
                >
                  {i < step ? "✓" : i + 1}
                </div>
                <span
                  className={cn(
                    "text-xs font-medium hidden sm:block",
                    i <= step ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  {label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-2 mb-4 transition-colors",
                    i < step ? "bg-primary" : "bg-border",
                  )}
                />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Form card */}
        <div className="bg-card rounded-2xl border border-border shadow-sm p-6">
          <form onSubmit={handleSubmit(onSubmit)}>
            {/* Step 0: Skills */}
            {step === 0 && (
              <div id="tour-skills" className="space-y-3">
                <div>
                  <Label className="text-base font-semibold text-foreground">
                    What skills do you have?
                  </Label>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Type to search or pick from the list. Press Enter or comma
                    to add.
                  </p>
                </div>
                <Controller
                  control={control}
                  name="skills"
                  render={({ field }) => (
                    <TagInput
                      value={field.value}
                      onChange={field.onChange}
                      suggestions={SKILL_OPTIONS}
                      placeholder="e.g. Python, React, SQL…"
                    />
                  )}
                />
                {errors.skills && (
                  <p className="text-sm text-destructive">
                    {errors.skills.message}
                  </p>
                )}
              </div>
            )}

            {/* Step 1: Interests */}
            {step === 1 && (
              <div className="space-y-3">
                <div>
                  <Label className="text-base font-semibold text-foreground">
                    What are you interested in?
                  </Label>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Pick domains or topics you enjoy or want to work in.
                  </p>
                </div>
                <Controller
                  control={control}
                  name="interests"
                  render={({ field }) => (
                    <TagInput
                      value={field.value}
                      onChange={field.onChange}
                      suggestions={INTEREST_SUGGESTIONS}
                      placeholder="e.g. AI, Design, Healthcare…"
                    />
                  )}
                />
                {errors.interests && (
                  <p className="text-sm text-destructive">
                    {errors.interests.message}
                  </p>
                )}
              </div>
            )}

            {/* Step 2: Education */}
            {step === 2 && (
              <div className="space-y-3">
                <div>
                  <Label className="text-base font-semibold text-foreground">
                    Highest level of education
                  </Label>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Or your current level if still studying.
                  </p>
                </div>
                <Controller
                  control={control}
                  name="education_level"
                  render={({ field }) => (
                    <div className="grid gap-2">
                      {EDUCATION_OPTIONS.map((opt) => (
                        <label
                          key={opt.value}
                          className={cn(
                            "flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-colors",
                            field.value === opt.value
                              ? "border-primary bg-primary/5"
                              : "border-border hover:border-primary/40",
                          )}
                        >
                          <input
                            type="radio"
                            className="sr-only"
                            value={opt.value}
                            checked={field.value === opt.value}
                            onChange={() => field.onChange(opt.value)}
                          />
                          <div
                            className={cn(
                              "h-4 w-4 rounded-full border-2 flex items-center justify-center shrink-0",
                              field.value === opt.value
                                ? "border-primary"
                                : "border-border",
                            )}
                          >
                            {field.value === opt.value && (
                              <div className="h-2 w-2 rounded-full bg-primary" />
                            )}
                          </div>
                          <span className="text-sm font-medium text-foreground">
                            {opt.label}
                          </span>
                        </label>
                      ))}
                    </div>
                  )}
                />
              </div>
            )}

            {/* Step 3: Personality */}
            {step === 3 && (
              <div className="space-y-6">
                <div>
                  <Label className="text-base font-semibold text-foreground">
                    How would you describe yourself?
                  </Label>
                  <p className="text-sm text-muted-foreground mt-0.5">
                    Drag each slider to where you naturally sit.
                  </p>
                </div>
                {PERSONALITY_TRAITS.map((trait) => (
                  <Controller
                    key={trait.key}
                    control={control}
                    name={`personality.${trait.key}`}
                    render={({ field }) => (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-foreground">
                            {trait.label}
                          </span>
                          <span className="text-xs text-muted-foreground tabular-nums w-8 text-right">
                            {field.value}
                          </span>
                        </div>
                        <Slider
                          min={0}
                          max={100}
                          step={1}
                          value={[field.value]}
                          onValueChange={([v]) => field.onChange(v)}
                        />
                        <div className="flex justify-between text-xs text-muted-foreground/70">
                          <span>{trait.low}</span>
                          <span>{trait.high}</span>
                        </div>
                      </div>
                    )}
                  />
                ))}
              </div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8 pt-4 border-t border-border">
              <Button
                type="button"
                variant="ghost"
                onClick={back}
                disabled={step === 0}
                className="text-muted-foreground"
              >
                Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button type="button" onClick={next}>
                  Continue →
                </Button>
              ) : (
                <Button type="submit">Find My Careers →</Button>
              )}
            </div>

            {submitError && (
              <p className="mt-3 text-sm text-center text-destructive">
                {submitError}
              </p>
            )}
          </form>
        </div>

        <p className="mt-4 text-center text-xs text-muted-foreground/70">
          Step {step + 1} of {STEPS.length}
        </p>
      </div>
    </div>
  );
}
