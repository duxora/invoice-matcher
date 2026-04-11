import { Phases } from '../lib/tokens'

interface PhaseChipProps {
  phase: (typeof Phases)[number]
  count: number
  active: boolean
  onClick: () => void
}

export default function PhaseChip({ phase, count, active, onClick }: PhaseChipProps) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-medium
        transition-all duration-150 select-none
        ${phase.color}
        ${active
          ? 'ring-2 ring-offset-1 ring-offset-transparent ring-white/20 shadow-sm scale-105'
          : 'opacity-60 hover:opacity-90 hover:scale-[1.02]'
        }
      `}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${phase.dot} ${active ? 'opacity-100' : 'opacity-70'}`} />
      <span>{phase.label}</span>
      {count > 0 && (
        <span className="bg-white/15 px-1.5 py-px rounded-full text-[10px] font-bold">{count}</span>
      )}
    </button>
  )
}
