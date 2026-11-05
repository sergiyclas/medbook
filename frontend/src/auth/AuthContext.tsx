import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { api, getToken, setToken } from '../api/client'
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
    api<Me>('/auth/me')
      .then(setUser)
      .catch(() => setToken(null))
      .finally(() => setReady(true))
  }, [])

  const value = useMemo(
    () => ({ user, ready, login, acceptToken, logout, refresh }),
    [user, ready, login, acceptToken, logout, refresh],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
