import type {
  SchedulerTask,
  RunRecord,
  ErrorRecord,
  SchedulerStats,
  Ticket,
  Notification,
  HealthCheck,
  LogResponse,
  Approval,
  TaskDetailResponse,
} from '../types'

const BASE = '/scheduler/api'

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

async function postForm(path: string, data: Record<string, string | number | boolean>): Promise<Response> {
  const formData = new FormData()
  for (const [key, value] of Object.entries(data)) {
    formData.append(key, String(value))
  }
  const res = await fetch(`/scheduler${path}`, { method: 'POST', body: formData })
  return res
}

async function postJson(path: string): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, { method: 'POST' })
  return res
}

export const schedulerApi = {
  getTasks: () => fetchJson<SchedulerTask[]>('/tasks'),

  getTask: (slug: string) => fetchJson<TaskDetailResponse>(`/tasks/${slug}`),

  getStats: () => fetchJson<SchedulerStats>('/stats'),

  getHistory: (params?: { task?: string; n?: number }) => {
    const qs = new URLSearchParams()
    if (params?.task) qs.set('task', params.task)
    if (params?.n) qs.set('n', String(params.n))
    const query = qs.toString() ? `?${qs.toString()}` : ''
    return fetchJson<RunRecord[]>(`/history${query}`)
  },

  getErrors: (task?: string) => {
    const qs = task ? `?task=${encodeURIComponent(task)}` : ''
    return fetchJson<ErrorRecord[]>(`/errors${qs}`)
  },

  getTickets: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return fetchJson<Ticket[]>(`/tickets${qs}`)
  },

  getNotifications: (showAll?: boolean) => {
    const qs = showAll ? '?all=true' : ''
    return fetchJson<Notification[]>(`/notifications${qs}`)
  },

  getDoctor: () => fetchJson<HealthCheck[]>('/doctor'),

  getLogs: (slug: string) => fetchJson<LogResponse>(`/logs/${slug}`),

  getApprovals: () => fetchJson<Approval[]>('/approvals'),

  runTask: (slug: string) => postJson(`/run/${slug}`),

  toggleTask: (slug: string) => postJson(`/toggle/${slug}`),

  resolveTicket: (id: number) => postJson(`/tickets/${id}/approve`),

  markNotificationsRead: () => postJson('/notifications/mark-read'),

  approveApproval: (id: number) => postJson(`/approvals/${id}/approve`),

  rejectApproval: (id: number) => postJson(`/approvals/${id}/reject`),

  createTask: (data: {
    name: string
    schedule: string
    prompt: string
    model: string
    max_turns: number
    timeout: number
    tools: string
    workdir: string
    enabled: boolean
  }) => postForm('/tasks-new', data as Record<string, string | number | boolean>),

  updatePrompt: (slug: string, prompt: string) =>
    postForm(`/api/update-prompt/${slug}`, { prompt }),
}
