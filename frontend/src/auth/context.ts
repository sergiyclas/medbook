import { createContext, useContext } from 'react'
import type { Me, Role } from '../api/types'

export interface AuthState {
  user: Me | null
  ready: boolean
  login: (email: string, password: string) => Promise<Me>
  acceptToken: (token: string) => Promise<Me>
  logout: () => void
  refresh: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}

export const HOME_BY_ROLE: Record<Role, string> = {
  patient: '/my',
  doctor: '/doctor',
  admin: '/admin',
}
