import type { KBDomain, KBConfidence } from '../types'

export const KB_DOMAINS: KBDomain[] = [
  'tech-trends',
  'coding-skills',
  'system-design',
  'leadership',
  'startup',
]

// Color-coded domain badges
const DOMAIN_COLORS: Record<KBDomain, string> = {
  'tech-trends': 'bg-blue-900/60 text-blue-300 border-blue-700',
  'coding-skills': 'bg-emerald-900/60 text-emerald-300 border-emerald-700',
  'system-design': 'bg-purple-900/60 text-purple-300 border-purple-700',
  'leadership': 'bg-amber-900/60 text-amber-300 border-amber-700',
  'startup': 'bg-pink-900/60 text-pink-300 border-pink-700',
}

export function domainBadgeClass(domain: string): string {
  return (
    DOMAIN_COLORS[domain as KBDomain] ??
    'bg-gray-800/60 text-gray-400 border-gray-700'
  )
}

const CONFIDENCE_COLORS: Record<KBConfidence, string> = {
  high: 'bg-green-900/60 text-green-300 border-green-700',
  medium: 'bg-yellow-900/60 text-yellow-300 border-yellow-700',
  low: 'bg-red-900/60 text-red-300 border-red-700',
}

export function confidenceBadgeClass(confidence: string): string {
  return (
    CONFIDENCE_COLORS[confidence as KBConfidence] ??
    'bg-gray-800/60 text-gray-400 border-gray-700'
  )
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return iso
  }
}
