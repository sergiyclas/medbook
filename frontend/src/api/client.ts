const BASE = '/api/v1'
const TOKEN_KEY = 'medbook.token'
// Fired when the server rejects the saved token (expired or revoked)
export const SESSION_EXPIRED = 'medbook:session-expired'

export class ApiError extends Error {
  status: number
  code: string | null

  constructor(status: number, message: string, code: string | null) {
    super(message)
    this.status = status
    this.code = code
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    // private mode: the session simply will not survive a reload
  }
}

// Domain errors come as {detail, code}; FastAPI validation errors as
// {detail: [{loc, msg}]}. Both become one readable message.
function messageOf(body: unknown, status: number): [string, string | null] {
  if (body && typeof body === 'object' && 'detail' in body) {
    const { detail, code } = body as { detail: unknown; code?: string }
    if (typeof detail === 'string') return [detail, code ?? null]
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0] as { msg?: string; loc?: unknown[] }
      const field = first.loc?.slice(-1)[0]
      const text = (first.msg ?? 'Некоректні дані').replace(/^Value error, /, '')
      return [field && field !== 'body' ? `${text} (поле «${field}»)` : text, 'validation']
    }
  }
  if (status === 401) return ['Потрібно увійти', 'unauthorized']
  return [`Сервер відповів помилкою ${status}`, null]
}

type Query = Record<string, string | number | boolean | null | undefined>

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; query?: Query; form?: URLSearchParams } = {},
): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== null && value !== undefined && value !== '')
      url.searchParams.set(key, String(value))
  }
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let body: BodyInit | undefined
  if (options.form) {
    body = options.form
  } else if (options.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  let response: Response
  try {
    response = await fetch(url, { method: options.method ?? 'GET', headers, body })
  } catch {
    throw new ApiError(0, 'Немає зв’язку із сервером. Перевірте, чи запущено бекенд.', 'network')
  }
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const [message, code] = messageOf(data, response.status)
    if (response.status === 401 && token) {
      setToken(null)
      window.dispatchEvent(new Event(SESSION_EXPIRED))
    }
    throw new ApiError(response.status, message, code)
  }
  return data as T
}
