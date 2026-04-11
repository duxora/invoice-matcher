interface ProjectCardProps {
  label: string
  open: number
  inProgress: number
  done: number
  active: boolean
  onClick: () => void
}

export default function ProjectCard({ label, open, inProgress, done, active, onClick }: ProjectCardProps) {
  return (
    <button
      onClick={onClick}
      className={`
        group flex flex-col gap-2 px-3.5 py-2.5 rounded-xl border transition-all duration-150 text-left
        ${active
          ? 'border-blue-500/60 shadow-lg shadow-blue-500/10 bg-gradient-to-br from-blue-900/30 to-slate-800/60'
          : 'border-slate-700/50 hover:border-slate-500/70 hover:shadow-md hover:shadow-black/20'
        }
      `}
      style={{ background: active ? undefined : 'var(--wf-bg-card)' }}
    >
      <span className={`text-xs font-semibold truncate max-w-[140px] transition-colors ${
        active ? 'text-white' : 'text-slate-200 group-hover:text-white'
      }`}>
        {label}
      </span>
      <div className="flex items-center gap-3">
        <span className="flex items-center gap-1 text-[10px] font-semibold text-blue-300">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 inline-block" />
          {open}
        </span>
        <span className="flex items-center gap-1 text-[10px] font-semibold text-amber-300">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-400 inline-block" />
          {inProgress}
        </span>
        <span className="flex items-center gap-1 text-[10px] font-semibold text-emerald-300">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
          {done}
        </span>
      </div>
    </button>
  )
}
