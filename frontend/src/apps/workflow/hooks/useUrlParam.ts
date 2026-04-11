import { useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'

/**
 * Bind a single URL search param to state so it survives reloads.
 *
 * Falsy values (empty string, or equal to `defaultValue`) are stripped from
 * the URL to keep the query string clean. Updates use `replace` so filter
 * keystrokes don't spam the browser history.
 */
export function useUrlParam(
  key: string,
  defaultValue = '',
): [string, (next: string) => void] {
  const [params, setParams] = useSearchParams()
  const value = params.get(key) ?? defaultValue

  const setValue = useCallback(
    (next: string) => {
      setParams(
        (prev) => {
          const copy = new URLSearchParams(prev)
          if (!next || next === defaultValue) copy.delete(key)
          else copy.set(key, next)
          return copy
        },
        { replace: true },
      )
    },
    [key, defaultValue, setParams],
  )

  return [value, setValue]
}
