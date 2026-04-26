import { z } from "zod";

export const personalitySchema = z.object({
  openness: z.number().int().min(0).max(100),
  conscientiousness: z.number().int().min(0).max(100),
  extraversion: z.number().int().min(0).max(100),
  agreeableness: z.number().int().min(0).max(100),
  neuroticism: z.number().int().min(0).max(100),
});

export const profileSchema = z.object({
  skills: z
    .array(z.string().min(1))
    .min(1, "Add at least one skill"),
  interests: z
    .array(z.string().min(1))
    .min(1, "Add at least one interest"),
  education_level: z.enum([
    "high_school",
    "diploma",
    "bachelors",
    "masters",
    "phd",
  ]),
  personality: personalitySchema,
  constraints: z.record(z.unknown()).nullable().optional(),
});

export type ProfileFormValues = z.infer<typeof profileSchema>;
