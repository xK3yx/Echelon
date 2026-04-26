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

export interface RankedCareer {
  slug: string;
  name: string;
  category: string;
  fit_reasoning: string;
  strengths: string[];
  risks: string[];
  confidence: number;
  rule_scores: RuleScores;
  skill_gaps: SkillGap[];
  roadmap: RoadmapPhase[];
}

export interface RecommendationResult {
  ranked_careers: RankedCareer[];
}

export interface RecommendationRead {
  id: string;
  profile_id: string;
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
