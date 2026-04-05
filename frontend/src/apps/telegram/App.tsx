import { useState, useCallback } from 'react'
import useSWR from 'swr'
import { useTelegramStatus } from './hooks/useTelegramStatus'
import { restartBot, fetchLogs } from './lib/api'

// ── static data (sourced from dashboard.html / routes.py) ─────────────────

const BOT_CONFIG = [
  { label: 'Bot Username', value: '@raikuna_dd_bot', mono: false },
  { label: 'Chat ID', value: '2010918973', mono: true },
  { label: 'Launchd Service', value: 'com.ducduong.telegram-bridge', mono: true },
  { label: 'Log File', value: '~/.local/log/telegram-bridge.err', mono: true },
  { label: 'Plugin Directory', value: 'telegram-bridge/src/telegram_bridge/plugins/', mono: true },
] as const

// System commands are always present (from routes.py _get_all_commands)
const SYSTEM_COMMANDS = [
  { name: '/help', plugin: 'system', description: 'Show all commands' },
  { name: '/start', plugin: 'system', description: 'Welcome message' },
  { name: '/ping', plugin: 'system', description: 'Check bot is alive' },
]

// ── small presentational components ───────────────────────────────────────

function StatCard({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4">
      <div className="text-gray-500 text-xs uppercase tracking-wide mb-1">{label}</div>
      {children}
    </div>
  )
}

function SectionCard({
  title,
  children,
}: {
  title: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg">
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-base font-semibold text-gray-100">{title}</h2>
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

// ── status indicator ───────────────────────────────────────────────────────

function StatusIndicator({ running, isLoading }: { running: boolean; isLoading: boolean }) {
  if (isLoading) {
    return <div className="text-2xl font-bold text-gray-500">Checking…</div>
  }
  return (
    <div className={`flex items-center gap-2 text-2xl font-bold ${running ? 'text-green-400' : 'text-red-400'}`}>
      <span
        className={`inline-block w-2.5 h-2.5 rounded-full ${running ? 'bg-green-400' : 'bg-red-400'}`}
        aria-hidden="true"
      />
      {running ? 'Running' : 'Stopped'}
    </div>
  )
}

// ── restart button ─────────────────────────────────────────────────────────

function RestartButton({ onRefresh }: { onRefresh: () => void }) {
  const [state, setState] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle')

  const handleRestart = useCallback(async () => {
    if (state === 'loading') return
    const confirmed = window.confirm('Restart the Telegram bot?')
    if (!confirmed) return

    setState('loading')
    try {
      await restartBot()
      setState('ok')
      onRefresh()
      setTimeout(() => setState('idle'), 3000)
    } catch {
      setState('error')
      setTimeout(() => setState('idle'), 3000)
    }
  }, [state, onRefresh])

  const label =
    state === 'loading'
      ? 'Restarting…'
      : state === 'ok'
        ? 'Restarted'
        : state === 'error'
          ? 'Error'
          : 'Restart'

  const colorClass =
    state === 'ok'
      ? 'bg-green-700 hover:bg-green-600 text-white'
      : state === 'error'
        ? 'bg-red-700 text-white'
        : 'bg-gray-700 hover:bg-gray-600 text-gray-100'

  return (
    <button
      onClick={handleRestart}
      disabled={state === 'loading'}
      className={`px-3 py-1.5 text-sm font-medium rounded transition-colors disabled:opacity-50 ${colorClass}`}
    >
      {label}
    </button>
  )
}

// ── logs panel ─────────────────────────────────────────────────────────────

function LogsPanel() {
  const { data: logs, isLoading, error } = useSWR<string>(
    'telegram-logs',
    fetchLogs,
    { refreshInterval: 10_000 },
  )

  return (
    <div className="p-3 bg-gray-950 rounded overflow-x-auto max-h-80 overflow-y-auto">
      {isLoading && <span className="text-xs text-gray-500">Loading logs…</span>}
      {error && <span className="text-xs text-red-400">Failed to load logs.</span>}
      {logs && (
        <pre className="text-xs text-gray-400 whitespace-pre-wrap break-all leading-relaxed">
          {logs}
        </pre>
      )}
    </div>
  )
}

// ── main page ──────────────────────────────────────────────────────────────

export default function TelegramApp() {
  const { running, service, isLoading, error, refresh } = useTelegramStatus()

  return (
    <div className="p-6 space-y-6 bg-gray-950 min-h-full text-gray-100">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Telegram Bridge</h1>
        <div className="flex items-center gap-3">
          {error && (
            <span className="text-xs text-red-400">Health check failed</span>
          )}
          <RestartButton onRefresh={refresh} />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Status">
          <StatusIndicator running={running} isLoading={isLoading} />
        </StatCard>

        <StatCard label="Commands">
          <div className="text-2xl font-bold text-blue-400">{SYSTEM_COMMANDS.length}+</div>
        </StatCard>

        <StatCard label="Service">
          <div className="text-sm font-mono text-gray-400 mt-1">launchd</div>
        </StatCard>

        <StatCard label="Manager">
          <div className="text-sm font-mono text-gray-400 mt-1 truncate" title={service}>
            {service || 'com.ducduong.telegram-bridge'}
          </div>
        </StatCard>
      </div>

      {/* Two-column: plugins + bot config */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Plugins — data comes from Python file scanning, no JSON API yet */}
        <SectionCard title="Registered Plugins">
          <div className="text-sm text-gray-500 italic">
            Plugin data requires a JSON API endpoint.{' '}
            <a
              href="/telegram-bridge"
              className="text-blue-400 hover:text-blue-300 underline"
            >
              View in legacy dashboard
            </a>
          </div>
        </SectionCard>

        {/* Bot config */}
        <SectionCard title="Bot Configuration">
          <dl className="space-y-2 text-sm">
            {BOT_CONFIG.map(({ label, value, mono }) => (
              <div key={label}>
                <dt className="text-gray-500 text-xs uppercase tracking-wide">{label}</dt>
                <dd className={`mt-0.5 ${mono ? 'font-mono text-xs text-gray-300' : 'font-medium text-gray-100'}`}>
                  {value}
                </dd>
              </div>
            ))}
          </dl>
        </SectionCard>
      </div>

      {/* Command reference */}
      <SectionCard title="Command Reference">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase tracking-wide border-b border-gray-700">
              <th className="pb-2 pr-4">Command</th>
              <th className="pb-2 pr-4">Plugin</th>
              <th className="pb-2">Description</th>
            </tr>
          </thead>
          <tbody>
            {SYSTEM_COMMANDS.map((cmd) => (
              <tr key={cmd.name} className="border-b border-gray-800/50 last:border-0">
                <td className="py-2 pr-4">
                  <code className="text-xs bg-gray-800 text-blue-400 px-1.5 py-0.5 rounded">
                    {cmd.name}
                  </code>
                </td>
                <td className="py-2 pr-4">
                  <span className="text-xs bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded">
                    {cmd.plugin}
                  </span>
                </td>
                <td className="py-2 text-gray-400 text-xs">{cmd.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-gray-600 italic">
          Plugin-registered commands are discoverable via the legacy dashboard.
        </p>
      </SectionCard>

      {/* Logs */}
      <SectionCard title="Recent Logs">
        <LogsPanel />
      </SectionCard>
    </div>
  )
}
