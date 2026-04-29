export interface PersonalityScores {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
}

export type EducationLevel =
  | "high_school"
  | "diploma"
  | "bachelors"
  | "masters"
  | "phd";

export interface ProfileCreate {
  skills: string[];
  interests: string[];
  education_level: EducationLevel;
  personality: PersonalityScores;
  constraints?: Record<string, unknown> | null;
}

export interface ProfileRead extends ProfileCreate {
  id: string;
  user_id: string;
  created_at: string;
}

export interface CareerRead {
  id: string;
  name: string;
  slug: string;
  description: string;
  required_skills: string[];
  optional_skills: string[];
  personality_fit: PersonalityScores;
  difficulty: "low" | "medium" | "high";
  growth_potential: "low" | "medium" | "high";
  category: string;
}

export interface SkillGap {
  skill: string;
  difficulty: "easy" | "medium" | "hard";
}

export interface RoadmapPhase {
  phase: "Beginner" | "Intermediate" | "Advanced";
  skills: string[];
  projects: string[];
  duration_weeks: number;
}

export interface RuleScores {
  total: number;
  skill: number;
  optional: number;
  personality: number;
  interest: number;
}

export type CareerSource = "onet" | "manual" | "llm_proposed";

export interface RankedCareer {
  slug: string;
  name: string;
  category: string;
  source: CareerSource;
  external_url?: string | null;
  fit_reasoning: string;
  strengths: string[];
  risks: string[];
  confidence: number;
  rule_scores: RuleScores;
  skill_gaps: SkillGap[];
  roadmap: RoadmapPhase[];
}

export interface ProposedCareer {
  id: string;
  name: string;
  slug: string;
  category: string;
  description: string;
  source: "llm_proposed";
  verified: false;
  rationale: string;
}

export interface RecommendationResult {
  ranked_careers: RankedCareer[];
  proposed_careers: ProposedCareer[];
}

export interface RecommendationRead {
  id: string;
  profile_id: string;
  result: RecommendationResult;
  model_used: string;
  is_public: boolean;
  created_at: string;
}

export interface RecommendationPublic {
  id: string;
  result: RecommendationResult;
  model_used: string;
  created_at: string;
}

export interface AnalyzeResponse {
  profile_id: string;
  career_slug: string;
  career_name: string;
  skill_gaps: SkillGap[];
}

// ── Resume parsing ─────────────────────────────────────────────────────────

export interface ExtractedProfile {
  name: string | null;
  email: string | null;
  skills: string[];
  education_level: EducationLevel | null;
  interests: string[];
  years_experience: number | null;
  summary: string | null;
}

export interface ResumeParseResponse {
  extracted: ExtractedProfile;
  confidence: number;
  warnings: string[];
}

// ── Course recommendations ─────────────────────────────────────────────────

export type CourseProvider = "youtube" | "tavily";

export interface Course {
  title: string;
  url: string;
  provider: CourseProvider;
  thumbnail: string | null;
  channel: string;
  description: string;
  relevance_score: number;
  rationale: string;
}

export interface CourseRecommendResponse {
  courses: Course[];
  source_note: string;
}
