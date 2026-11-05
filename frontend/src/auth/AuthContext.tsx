import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { ApiError, SESSION_EXPIRED, api, getToken, setToken } from '../api/client'
import type { Me, Token } from '../api/types'
import { AuthContext } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null)
  // Without a saved token there is nothing to restore
  const [ready, setReady] = useState(() => !getToken())

  const acceptToken = useCallback(async (token: string) => {
    setToken(token)
    const me = await api<Me>('/auth/me')
    setUser(me)
    return me
  }, [])

  const login = useCallback(
    async (email: string, password: string) => {
      const form = new URLSearchParams({ username: email, password })
      const { access_token } = await api<Token>('/auth/login', { method: 'POST', form })
      return acceptToken(access_token)
    },
    [acceptToken],
  )

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const refresh = useCallback(async () => {
    setUser(await api<Me>('/auth/me'))
  }, [])

  // Restore the session from a saved token; an expired one is simply dropped
  useEffect(() => {
    if (!getToken()) return
    // Only a rejected token is dropped; a network error keeps it for the next load
    api<Me>('/auth/me')
      .then(setUser)
      .catch((err) => err instanceof ApiError && err.status === 401 && setToken(null))
      .finally(() => setReady(true))
  }, [])

  // An expired token mid-session signs the user out, and RequireRole sends them to login
  useEffect(() => {
    const onExpired = () => setUser(null)
    window.addEventListener(SESSION_EXPIRED, onExpired)
    return () => window.removeEventListener(SESSION_EXPIRED, onExpired)
  }, [])

  const value = useMemo(
    () => ({ user, ready, login, acceptToken, logout, refresh }),
    [user, ready, login, acceptToken, logout, refresh],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
