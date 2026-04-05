import { useState, useEffect, useRef } from 'react'
import type { KBEntry, KBDomain } from '../types'
import { searchEntries } from '../lib/api'

const DEBOUNCE_MS = 300

interface UseKBSearchResult {
  entries: KBEntry[]
  isLoading: boolean
  error: string | null
  query: string
  domain: string
  setQuery: (q: string) => void
  setDomain: (d: string) => void
}

export function useKBSearch(): UseKBSearchResult {
  const [query, setQuery] = useState('')
  const [domain, setDomain] = useState('')
  const [entries, setEntries] = useState<KBEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current)

    if (!query || query.length < 2) {
      setEntries([])
      setIsLoading(false)
      setError(null)
      return
    }

    timerRef.current = setTimeout(async () => {
      // Cancel prior in-flight request
      abortRef.current?.abort()
      abortRef.current = new AbortController()

      setIsLoading(true)
      setError(null)

      try {
        const results = await searchEntries({
          q: query,
          domain: domain as KBDomain | undefined,
        })
        setEntries(results)
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message)
        }
      } finally {
        setIsLoading(false)
      }
    }, DEBOUNCE_MS)

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [query, domain])

  return { entries, isLoading, error, query, domain, setQuery, setDomain }
}
