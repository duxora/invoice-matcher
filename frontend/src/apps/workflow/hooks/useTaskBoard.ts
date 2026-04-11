import useSWR from 'swr'
import type { Task, ProjectSummary } from '../types'

const fetcher = (url: string) => fetch(url).then((r) => r.json())

export function useTaskBoard(projectFilter: string, statusFilter: string) {
  const params = new URLSearchParams()
  if (projectFilter) params.set('project', projectFilter)
  // statusFilter values: '' = active (open+in_progress, excludes backlog), 'backlog', 'open', 'in_progress', 'done', 'all'
  if (statusFilter === '') {
    params.set('status', 'open,in_progress')
  } else if (statusFilter !== 'all') {
    params.set('status', statusFilter)
  }

  const { data: tasks, error: tasksError, mutate: mutateTasks } = useSWR<Task[]>(
    `/workflow/api/tasks?${params}`,
    fetcher,
    { refreshInterval: 5000 },
  )

  const { data: projects, error: projectsError } = useSWR<ProjectSummary[]>(
    '/workflow/api/dashboard',
    fetcher,
    { refreshInterval: 10000 },
  )

  return { tasks, projects, tasksError, projectsError, mutateTasks }
}
