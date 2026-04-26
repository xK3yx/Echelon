import type {
  AnalyzeResponse,
  CareerRead,
  ProfileCreate,
  ProfileRead,
  RecommendationRead,
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

  createRecommendation: (profileId: string, refresh = false) =>
    request<RecommendationRead>("/recommendations", {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, refresh }),
    }),

  getRecommendation: (id: string) =>
    request<RecommendationRead>(`/recommendations/${id}`),

  analyze: (profileId: string, careerSlug: string) =>
    request<AnalyzeResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId, career_slug: careerSlug }),
    }),
};
