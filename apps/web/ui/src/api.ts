export type Health = { status: string };
export type Years = { years: string[] };

export type JobRequest = {
  year: number;
  language: string;
  selection: {
    mode: "all" | "indices" | "regions_sectors";
    regions: number[];
    sectors: number[];
    indices: number[];
  };
  analysis: { type: string; impacts: string[]; params: Record<string, unknown> };
};

export type JobCreateResponse = { job_id: string; cached?: boolean };
export type JobStatus = { job_id: string; state: "queued" | "running" | "done" | "failed"; progress: number; message?: string | null };
export type JobResult = { job_id: string; result: unknown };
export type Impacts = { impacts: { impact: string; unit?: string; decimal_places?: number }[] };
export type Languages = { languages: string[] };
export type Hierarchy = { names: string[]; tree: Record<string, unknown>; leaves: { index: number; path: string[] }[] };

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => fetchJson<Health>("/api/v1/health"),
  years: () => fetchJson<Years>("/api/v1/meta/years"),
  languages: (year: number) => fetchJson<Languages>(`/api/v1/meta/languages?year=${encodeURIComponent(year)}`),
  impacts: (year: number, language: string) =>
    fetchJson<Impacts>(`/api/v1/impacts?year=${encodeURIComponent(year)}&language=${encodeURIComponent(language)}`),
  regionHierarchy: (year: number, language: string) =>
    fetchJson<Hierarchy>(`/api/v1/hierarchy/regions?year=${encodeURIComponent(year)}&language=${encodeURIComponent(language)}`),
  sectorHierarchy: (year: number, language: string) =>
    fetchJson<Hierarchy>(`/api/v1/hierarchy/sectors?year=${encodeURIComponent(year)}&language=${encodeURIComponent(language)}`),
  createJob: (payload: JobRequest) =>
    fetchJson<JobCreateResponse>("/api/v1/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }),
  jobStatus: (jobId: string) => fetchJson<JobStatus>(`/api/v1/jobs/${encodeURIComponent(jobId)}`),
  jobResult: (jobId: string) => fetchJson<JobResult>(`/api/v1/jobs/${encodeURIComponent(jobId)}/result`),
};
