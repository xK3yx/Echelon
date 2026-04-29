import type {
  AnalyzeResponse,
  CareerRead,
  CourseRecommendResponse,
  ProfileCreate,
  ProfileRead,
  RecommendationPublic,
  RecommendationRead,
  ResumeParseResponse,
} from "@/lib/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as {
      error?: { code?: string; message?: string };
    };
    throw new ApiError(
      res.status,
      body.error?.code ?? "UNKNOWN_ERROR",
      body.error?.message ?? `HTTP ${res.status}`,
    );
  }

  return res.json() as Promise<T>;
}

export const api = {
  createProfile: (data: ProfileCreate) =>
    request<ProfileRead>("/profiles", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getProfile: (id: string) => request<ProfileRead>(`/profiles/${id}`),

  listCareers: () => request<CareerRead[]>("/careers"),

  getCareer: (slug: string) => request<CareerRead>(`/careers/${slug}`),

  createRecommendation: (profileId: string, refresh = false, allowProposed = true) =>
    request<RecommendationRead>("/recommendations", {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, refresh, allow_proposed: allowProposed }),
    }),

  getRecommendation: (id: string) =>
    request<RecommendationRead>(`/recommendations/${id}`),

  analyze: (profileId: string, careerSlug: string) =>
    request<AnalyzeResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, career_slug: careerSlug }),
    }),

  shareRecommendation: (id: string) =>
    request<RecommendationRead>(`/recommendations/${id}/share`, { method: "POST" }),

  getPublicRecommendation: (id: string) =>
    request<RecommendationPublic>(`/recommendations/${id}/public`),

  getCourses: (careerSlug: string, careerName: string, gapSkills: string[]) =>
    request<CourseRecommendResponse>(
      `/courses/recommend?career_slug=${encodeURIComponent(careerSlug)}&career_name=${encodeURIComponent(careerName)}&skills=${encodeURIComponent(gapSkills.join(","))}`,
    ),

  /** Multipart upload — does not go through the JSON `request` helper. */
  parseResume: async (file: File): Promise<ResumeParseResponse> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/resume/parse`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({})) as {
        error?: { code?: string; message?: string };
      };
      throw new ApiError(
        res.status,
        body.error?.code ?? "UNKNOWN_ERROR",
        body.error?.message ?? `HTTP ${res.status}`,
      );
    }
    return res.json() as Promise<ResumeParseResponse>;
  },
};
