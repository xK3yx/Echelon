import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme-toggle";

const STEPS = [
  {
    number: "01",
    title: "Build your profile",
    description:
      "Enter your skills, interests, education level, and Big Five personality scores in a guided four-step form.",
  },
  {
    number: "02",
    title: "See your matches",
    description:
      "A deterministic scoring engine ranks ~200 O*NET occupations plus curated tech roles against your profile across skill, personality, and interest dimensions.",
  },
  {
    number: "03",
    title: "Get your roadmap",
    description:
      "An LLM explains why each top career fits you, flags your skill gaps, and maps a three-phase learning path.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <header className="border-b border-border bg-card">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-semibold text-foreground tracking-tight">
            Echelon
          </span>
          <div className="flex items-center gap-2">
            <a
              href="https://github.com/xK3yx/Echelon"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              GitHub
            </a>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-5xl mx-auto px-6 pt-28 pb-24 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl leading-tight">
            Find the career that fits{" "}
            <span className="text-primary">you</span>.
          </h1>
          <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed">
            Answer a few structured questions about your skills, personality,
            and goals. Echelon scores you against curated career paths and
            returns a ranked list with AI-generated reasoning and a learning
            roadmap — all in one request.
          </p>
          <div className="mt-10">
            <Button asChild size="lg" className="px-10">
              <Link href="/profile">Get started</Link>
            </Button>
          </div>
          <p className="mt-4 text-xs text-muted-foreground/70">
            No account required. Your profile is stored anonymously.
          </p>
        </section>

        {/* How it works */}
        <section className="border-t border-border">
          <div className="max-w-5xl mx-auto px-6 py-20">
            <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground/60 mb-12">
              How it works
            </p>
            <div className="grid sm:grid-cols-3 gap-10">
              {STEPS.map((step) => (
                <div key={step.number}>
                  <span className="text-3xl font-bold text-primary/20 select-none dark:text-primary/30">
                    {step.number}
                  </span>
                  <h3 className="mt-3 font-semibold text-foreground">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
                    {step.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="max-w-5xl mx-auto px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 text-sm text-muted-foreground">
          <span>Echelon v2.2 — portfolio project by xK3yx</span>
          <a
            href="https://github.com/xK3yx/Echelon"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-foreground transition-colors"
          >
            View source
          </a>
        </div>
        <div className="max-w-5xl mx-auto px-6 pb-4 text-xs text-muted-foreground/70 leading-relaxed">
          This product uses data from{" "}
          <a
            href="https://www.onetonline.org/"
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-foreground"
          >
            O*NET OnLine
          </a>{" "}
          by the U.S. Department of Labor, Employment and Training Administration
          (USDOL/ETA), used under CC BY 4.0. O*NET® is a trademark of USDOL/ETA.
        </div>
      </footer>
    </div>
  );
}
