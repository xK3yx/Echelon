import Link from "next/link";
import { Button } from "@/components/ui/button";

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
      "A deterministic scoring engine ranks 20 curated careers against your profile across skill, personality, and interest dimensions.",
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
      <header className="border-b border-border">
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-semibold text-slate-900 tracking-tight">
            Echelon
          </span>
          <a
            href="https://github.com/xK3yx/Echelon"
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm text-slate-500 hover:text-slate-700 transition-colors"
          >
            GitHub
          </a>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="max-w-5xl mx-auto px-6 pt-28 pb-24 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl leading-tight">
            Find the career that fits{" "}
            <span className="text-indigo-600">you</span>.
          </h1>
          <p className="mt-6 text-lg text-slate-500 max-w-2xl mx-auto leading-relaxed">
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
          <p className="mt-4 text-xs text-slate-400">
            No account required. Your profile is stored anonymously.
          </p>
        </section>

        {/* How it works */}
        <section className="border-t border-border">
          <div className="max-w-5xl mx-auto px-6 py-20">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-12">
              How it works
            </p>
            <div className="grid sm:grid-cols-3 gap-10">
              {STEPS.map((step) => (
                <div key={step.number}>
                  <span className="text-3xl font-bold text-indigo-100 select-none">
                    {step.number}
                  </span>
                  <h3 className="mt-3 font-semibold text-slate-800">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm text-slate-500 leading-relaxed">
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
        <div className="max-w-5xl mx-auto px-6 h-14 flex items-center justify-between text-sm text-slate-400">
          <span>Echelon v2 — portfolio project by xK3yx</span>
          <a
            href="https://github.com/xK3yx/Echelon"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-slate-600 transition-colors"
          >
            View source
          </a>
        </div>
      </footer>
    </div>
  );
}
