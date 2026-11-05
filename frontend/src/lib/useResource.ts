import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'

export interface Resource<T> {
  data: T | undefined
  error: ApiError | null
  loading: boolean
  reload: () => void
}

// Loads data for a screen and reloads it whenever `deps` change. A request that
// finishes after the inputs moved on is ignored, so fast clicks never show
// stale results.
export function useResource<T>(load: () => Promise<T>, deps: unknown[]): Resource<T> {
  const [data, setData] = useState<T>()
  const [error, setError] = useState<ApiError | null>(null)
  const [loading, setLoading] = useState(true)
  const [version, setVersion] = useState(0)
  const reload = useCallback(() => setVersion((v) => v + 1), [])

  useEffect(() => {
    let current = true
    setLoading(true)
    load()
      .then((result) => {
        if (!current) return
        setData(result)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!current) return
        setError(err instanceof ApiError ? err : new ApiError(0, String(err), null))
      })
      .finally(() => current && setLoading(false))
    return () => {
      current = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, version])

  return { data, error, loading, reload }
}

// Wraps a mutation: tracks "busy", turns failures into a message for the form
export function useAction() {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = useCallback(async <T>(action: () => Promise<T>): Promise<T | undefined> => {
    setBusy(true)
    setError(null)
    try {
      return await action()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : String(err))
      return undefined
    } finally {
      setBusy(false)
    }
  }, [])

  return { busy, error, setError, run }
}
