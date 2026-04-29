"use client";

import * as React from "react";
import Joyride, { type CallBackProps, STATUS, type Step } from "react-joyride";
import { useTheme } from "next-themes";

const STORAGE_KEY = "echelon_tour_completed";

const STEPS: Step[] = [
  {
    target: "body",
    placement: "center",
    disableBeacon: true,
    title: "Welcome to Echelon",
    content:
      "This quick tour shows you how to get the most out of your career analysis. It takes under a minute.",
  },
  {
    target: "#tour-resume",
    placement: "bottom",
    disableBeacon: true,
    title: "Import from your resume",
    content:
      "Drop a PDF, DOCX, or TXT resume and Echelon will pre-fill your skills, interests, and education automatically. Completely optional.",
  },
  {
    target: "#tour-skills",
    placement: "bottom",
    disableBeacon: true,
    title: "Add your skills",
    content:
      "Type your technical and professional skills one at a time, or pick from suggestions. The more accurate, the better your matches.",
  },
  {
    target: "#tour-steps",
    placement: "bottom",
    disableBeacon: true,
    title: "Complete all four steps",
    content:
      'Move through Skills → Interests → Education → Personality. Each section takes about 30 seconds. Hit "Get my results" on the final step.',
  },
];

export function OnboardingTour() {
  const [run, setRun] = React.useState(false);
  const { resolvedTheme } = useTheme();

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) setRun(true);
  }, []);

  const handleCallback = (data: CallBackProps) => {
    const { status } = data;
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      localStorage.setItem(STORAGE_KEY, "1");
      setRun(false);
    }
  };

  const isDark = resolvedTheme === "dark";

  return (
    <Joyride
      steps={STEPS}
      run={run}
      continuous
      showSkipButton
      showProgress
      callback={handleCallback}
      styles={{
        options: {
          primaryColor: "hsl(239 84% 67%)",
          backgroundColor: isDark ? "#1c1c27" : "#ffffff",
          textColor: isDark ? "#e5e7eb" : "#1a1a2e",
          arrowColor: isDark ? "#1c1c27" : "#ffffff",
          overlayColor: "rgba(0,0,0,0.45)",
          zIndex: 9999,
        },
        tooltipTitle: {
          fontSize: "14px",
          fontWeight: 700,
          marginBottom: "6px",
        },
        tooltipContent: {
          fontSize: "13px",
          lineHeight: 1.6,
          padding: "4px 0",
        },
        buttonNext: {
          borderRadius: "6px",
          fontSize: "13px",
          fontWeight: 600,
        },
        buttonBack: {
          fontSize: "13px",
          color: isDark ? "#9ca3af" : "#6b7280",
        },
        buttonSkip: {
          fontSize: "12px",
          color: isDark ? "#6b7280" : "#9ca3af",
        },
      }}
      locale={{
        back: "Back",
        close: "Close",
        last: "Done",
        next: "Next",
        skip: "Skip tour",
      }}
    />
  );
}
