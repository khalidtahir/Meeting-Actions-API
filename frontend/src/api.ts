const API_BASE = import.meta.env.VITE_API_URL ?? '/api';

function url(path: string): string {
  const base = API_BASE.replace(/\/$/, '');
  const p = path.startsWith('/') ? path : `/${path}`;
  return base ? `${base}${p}` : p;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url(path), {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error((err as { detail?: string }).detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
}

export interface ProjectDetail extends Project {
  meeting_count: number;
}

export interface ActionItem {
  id: string;
  meeting_id: string;
  meeting_title?: string;
  type: string;
  description: string;
  confidence: number;
  status: 'OPEN' | 'COMPLETED' | 'CARRYOVER';
  week_number?: number;
  owner?: string;
}

export interface PriorActionRef {
  id: string;
  description: string;
  owner?: string;
}

export interface NewActionItem {
  description: string;
  owner?: string;
}

export interface ReconciliationProposal {
  completed: PriorActionRef[];
  carryover: PriorActionRef[];
  new_actions: NewActionItem[];
  risk_flags: string[];
  summary: string;
}

export interface ProposalResponse {
  current_actions: ActionItem[];
  proposal: ReconciliationProposal;
}

export const api = {
  listProjects: () => request<Project[]>('/projects'),
  createProject: (data: { name: string; description?: string }) =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id: string) => request<ProjectDetail>(`/projects/${id}`),
  getProjectActions: (projectId: string) =>
    request<ActionItem[]>(`/projects/${projectId}/actions`),
  createProjectAction: (projectId: string, data: { description: string; type?: string; owner?: string }) =>
    request<ActionItem>(`/projects/${projectId}/actions`, { method: 'POST', body: JSON.stringify(data) }),
  getProposal: (
    projectId: string,
    data: {
      meeting_title: string;
      transcript: string;
      week_number: number;
      previous_proposal?: ReconciliationProposal | null;
      rejection_feedback?: string | null;
    }
  ) =>
    request<ProposalResponse>(`/projects/${projectId}/reconcile/proposal`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  applyProposal: (
    projectId: string,
    data: {
      meeting_title: string;
      transcript: string;
      week_number: number;
      proposal: ReconciliationProposal;
    }
  ) =>
    request<{ meeting_id: string; actions_completed: number; actions_carried_over: number; actions_new: number }>(
      `/projects/${projectId}/reconcile/apply`,
      { method: 'POST', body: JSON.stringify(data) }
    ),
  updateAction: (meetingId: string, actionId: string, data: { status?: string; description?: string; owner?: string }) =>
    request<ActionItem>(`/meetings/${meetingId}/actions/${actionId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteAction: (meetingId: string, actionId: string) =>
    request<void>(`/meetings/${meetingId}/actions/${actionId}`, { method: 'DELETE' }),
};
