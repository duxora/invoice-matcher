import { useEffect, useState } from 'react'
import useSWR, { useSWRConfig } from 'swr'
import type { ProjectSummary } from '../types'

// ── types ──────────────────────────────────────────────────────────────────

interface DomainMapping {
  domain: string
  project_id: string
  pattern: string | null
}

// ── fetcher ────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then((r) => r.json())

// ── main component ─────────────────────────────────────────────────────────

interface DomainMapModalProps {
  projects: ProjectSummary[]
  onClose: () => void
}

export default function DomainMapModal({ projects, onClose }: DomainMapModalProps) {
  const { mutate } = useSWRConfig()
  const { data: mappings, error } = useSWR<DomainMapping[]>(
    '/workflow/api/domain-map',
    fetcher,
  )

  const [newDomain, setNewDomain] = useState('')
  const [newProjectId, setNewProjectId] = useState('')
  const [newPattern, setNewPattern] = useState('')
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Close on Escape key
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  async function handleAdd() {
    if (!newDomain.trim() || !newProjectId) {
      setFormError('Domain and project are required')
      return
    }
    setSaving(true)
    setFormError(null)
    try {
      const res = await fetch('/workflow/api/domain-map', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: newDomain.trim(),
          project_id: newProjectId,
          pattern: newPattern.trim() || undefined,
        }),
      })
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      await mutate('/workflow/api/domain-map')
      setNewDomain('')
      setNewProjectId('')
      setNewPattern('')
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Failed to add mapping')
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete({ domain, project_id }: { domain: string; project_id: string }) {
    try {
      const res = await fetch('/workflow/api/domain-map', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain, project_id }),
      })
      if (!res.ok) throw new Error(`API error: ${res.status}`)
      await mutate('/workflow/api/domain-map')
    } catch (e) {
      console.error('Failed to delete mapping:', e)
    }
  }

  const projectName = (id: string) =>
    projects.find((p) => p.project_id === id)?.project_name ?? id

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div
        className="fixed inset-0 z-50 flex items-center justify-center p-4"
        role="dialog"
        aria-modal="true"
        aria-label="Domain map settings"
      >
        <div
          className="w-full max-w-[520px] bg-gray-900 border border-gray-700 rounded-xl shadow-2xl flex flex-col max-h-[80vh]"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
            <h2 className="text-sm font-semibold text-gray-100">Domain Map</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-300 transition-colors w-6 h-6 flex items-center justify-center rounded hover:bg-gray-800"
              aria-label="Close"
            >
              ✕
            </button>
          </div>

          {/* Mappings table */}
          <div className="flex-1 overflow-y-auto">
            {error && (
              <p className="text-xs text-red-400 px-4 py-3">Failed to load domain mappings</p>
            )}
            {!mappings && !error && (
              <p className="text-xs text-gray-600 px-4 py-3">Loading...</p>
            )}
            {mappings && mappings.length === 0 && (
              <p className="text-xs text-gray-600 px-4 py-3">No mappings yet</p>
            )}
            {mappings && mappings.length > 0 && (
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-800">
                    <th className="text-left px-4 py-2 text-[10px] text-gray-500 uppercase tracking-wider font-medium">
                      Domain
                    </th>
                    <th className="text-left px-4 py-2 text-[10px] text-gray-500 uppercase tracking-wider font-medium">
                      Project
                    </th>
                    <th className="text-left px-4 py-2 text-[10px] text-gray-500 uppercase tracking-wider font-medium">
                      Pattern
                    </th>
                    <th className="w-8" />
                  </tr>
                </thead>
                <tbody>
                  {mappings.map((m, i) => (
                    <tr
                      key={`${m.domain}-${m.project_id}-${i}`}
                      className="border-b border-gray-800/50 hover:bg-gray-800/30 transition-colors"
                    >
                      <td className="px-4 py-2 text-gray-300">{m.domain}</td>
                      <td className="px-4 py-2 text-gray-400">{projectName(m.project_id)}</td>
                      <td className="px-4 py-2 text-gray-500">
                        {m.pattern ? (
                          <code className="text-[10px] bg-gray-800 px-1 rounded">{m.pattern}</code>
                        ) : (
                          <span className="text-gray-700">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2">
                        <button
                          onClick={() => handleDelete({ domain: m.domain, project_id: m.project_id })}
                          className="text-[10px] text-gray-600 hover:text-red-400 transition-colors"
                          aria-label={`Delete mapping for ${m.domain}`}
                        >
                          ✕
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {/* Add new mapping form */}
          <div className="border-t border-gray-700 px-4 py-3 shrink-0">
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Add Mapping</p>
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="text"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="domain"
                className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300 placeholder-gray-600 w-28"
                aria-label="Domain"
              />
              <select
                value={newProjectId}
                onChange={(e) => setNewProjectId(e.target.value)}
                className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300"
                aria-label="Project"
              >
                <option value="">Project...</option>
                {projects.map((p) => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.project_name}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={newPattern}
                onChange={(e) => setNewPattern(e.target.value)}
                placeholder="pattern (optional)"
                className="text-xs bg-gray-800 border border-gray-700 rounded px-2 py-1 text-gray-300 placeholder-gray-600 w-36"
                aria-label="Pattern"
              />
              <button
                onClick={handleAdd}
                disabled={saving || !newDomain.trim() || !newProjectId}
                className="text-xs px-3 py-1 bg-blue-900 border border-blue-700 rounded text-blue-300 hover:bg-blue-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {saving ? 'Adding...' : 'Add'}
              </button>
            </div>
            {formError && (
              <p className="text-[10px] text-red-400 mt-1.5">{formError}</p>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
