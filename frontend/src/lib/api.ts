/** API client for ResearchScout backend */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FetchOptions extends RequestInit {
  token?: string | null;
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { token, ...fetchOpts } = options;

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...fetchOpts,
    headers,
  });

  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new ApiError(data.detail || 'Request failed', res.status);
  }

  return res.json();
}

// ── Auth ────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export async function register(
  email: string,
  password: string,
  fullName: string
): Promise<TokenResponse> {
  return fetchApi<TokenResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, full_name: fullName }),
  });
}

export async function login(
  email: string,
  password: string
): Promise<TokenResponse> {
  return fetchApi<TokenResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function refreshToken(
  refreshTokenStr: string
): Promise<TokenResponse> {
  return fetchApi<TokenResponse>('/api/v1/auth/refresh', {
    method: 'POST',
    body: JSON.stringify({ refresh_token: refreshTokenStr }),
  });
}

// ── User ────────────────────────────────────────────

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  university: string | null;
  degree_level: string | null;
  gpa: number | null;
  country: string | null;
  preferred_countries: string[];
  preferred_domains: string[];
  career_goals: string | null;
  skills: { id: string; skill_name: string; proficiency: string | null }[];
  publications: { id: string; title: string; venue: string | null; year: number | null }[];
  projects: { id: string; title: string; description: string | null; technologies: string[] }[];
  research_interests: { id: string; topic: string; weight: number }[];
  created_at: string;
}

export async function getProfile(token: string): Promise<UserProfile> {
  return fetchApi<UserProfile>('/api/v1/users/profile', { token });
}

export async function updateProfile(
  token: string,
  data: Partial<UserProfile>
): Promise<UserProfile> {
  return fetchApi<UserProfile>('/api/v1/users/profile', {
    method: 'PUT',
    token,
    body: JSON.stringify(data),
  });
}

// ── Opportunities ───────────────────────────────────

export interface OpportunityBrief {
  id: string;
  title: string;
  opportunity_type: string;
  organization: string;
  country: string | null;
  city: string | null;
  location_type: string | null;
  research_areas: string[];
  funding_type: string | null;
  deadline: string | null;
  summary: string | null;
  confidence_score: number;
  date_discovered: string;
  is_active: boolean;
}

export interface OpportunityDetail extends OpportunityBrief {
  department: string | null;
  research_lab: string | null;
  professor: string | null;
  professor_email: string | null;
  keywords: string[];
  required_skills: string[];
  programming_languages: string[];
  required_gpa: number | null;
  eligibility_criteria: Record<string, unknown> | null;
  degree_levels: string[];
  publications_required: boolean;
  recommendation_letters: number | null;
  visa_requirements: string | null;
  salary_range: string | null;
  stipend: string | null;
  duration: string | null;
  start_date: string | null;
  application_link: string;
  documents_required: string[];
  contact_email: string | null;
  source_url: string;
  last_verified: string;
  authenticity_score: number;
}

export interface Recommendation {
  opportunity_id: string;
  score: number;
  match_reasons: string[];
  opportunity: Partial<OpportunityDetail>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface OpportunityFilters {
  opportunity_type?: string[];
  country?: string[];
  funding_type?: string[];
  research_area?: string;
  query?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_order?: string;
}

export async function getOpportunities(
  filters: OpportunityFilters = {}
): Promise<PaginatedResponse<OpportunityBrief>> {
  const params = new URLSearchParams();

  if (filters.opportunity_type) {
    filters.opportunity_type.forEach((t) => params.append('opportunity_type', t));
  }
  if (filters.country) {
    filters.country.forEach((c) => params.append('country', c));
  }
  if (filters.funding_type) {
    filters.funding_type.forEach((f) => params.append('funding_type', f));
  }
  if (filters.research_area) params.set('research_area', filters.research_area);
  if (filters.query) params.set('query', filters.query);
  if (filters.page) params.set('page', String(filters.page));
  if (filters.page_size) params.set('page_size', String(filters.page_size));
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.sort_order) params.set('sort_order', filters.sort_order);

  return fetchApi<PaginatedResponse<OpportunityBrief>>(
    `/api/v1/opportunities?${params.toString()}`
  );
}

export async function getTrendingOpportunities(
  limit = 10
): Promise<OpportunityBrief[]> {
  return fetchApi<OpportunityBrief[]>(
    `/api/v1/opportunities/trending?limit=${limit}`
  );
}

export async function getRecommendations(
  token: string,
  limit = 10
): Promise<{ recommendations: Recommendation[]; total: number }> {
  return fetchApi<{ recommendations: Recommendation[]; total: number }>(
    `/api/v1/opportunities/recommendations?limit=${limit}`,
    { token }
  );
}

export async function getOpportunityDetail(
  id: string
): Promise<OpportunityDetail> {
  return fetchApi<OpportunityDetail>(`/api/v1/opportunities/${id}`);
}

export async function saveOpportunity(
  id: string,
  token: string
): Promise<{ message: string }> {
  return fetchApi(`/api/v1/opportunities/${id}/save`, {
    method: 'POST',
    token,
  });
}

export async function unsaveOpportunity(
  id: string,
  token: string
): Promise<{ message: string }> {
  return fetchApi(`/api/v1/opportunities/${id}/save`, {
    method: 'DELETE',
    token,
  });
}

// ── Intelligence & Search ───────────────────────────

export async function semanticSearch(
  query: string,
  limit = 20
): Promise<{ query: string; results: any[]; total: number }> {
  return fetchApi(
    `/api/v1/search/semantic?q=${encodeURIComponent(query)}&limit=${limit}`
  );
}

export async function getGraphStats(): Promise<{ nodes: Record<string, number>; relationships: Record<string, number> }> {
  return fetchApi('/api/v1/graph/stats');
}

// ── Pipeline ────────────────────────────────────────

export async function triggerDiscovery(
  token: string,
  topics: string[],
  opportunityTypes?: string[],
  maxUrls?: number
): Promise<{ message: string }> {
  return fetchApi('/api/v1/pipeline/discover', {
    method: 'POST',
    token,
    body: JSON.stringify({
      topics,
      opportunity_types: opportunityTypes,
      max_urls: maxUrls || 20,
    }),
  });
}

export { ApiError };
