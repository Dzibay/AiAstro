import { clearSession, readSession } from '../composables/useSession.js'

export class ApiError extends Error {
  constructor(code, status) {
    super(code)
    this.code = code
    this.status = status
  }
}

const ERRORS = {
  unauthorized: 'Неверные данные для входа',
  email: 'Укажите корректную почту',
  password: 'Пароль должен быть не короче 8 символов',
  blocked: 'Аккаунт заблокирован',
  expired: 'Сессия истекла, войдите снова',
  exists: 'Такая почта уже зарегистрирована',
  setting: 'Эту настройку нельзя сохранить',
  missing: 'Такой страницы нет',
}

export function errorText(error) {
  if (error instanceof ApiError) {
    if (error.status >= 500) return 'Сервис временно недоступен'
    if (ERRORS[error.code]) return ERRORS[error.code]
    return 'Не получилось выполнить запрос'
  }
  return 'Нет связи с сервером'
}

export async function request(path, { method = 'GET', body, audience, auth = false } = {}) {
  const headers = { Accept: 'application/json' }
  const token = auth ? readSession(audience) : ''
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('network', 0)
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && auth) clearSession(audience)
    const code = data && typeof data.detail === 'string' ? data.detail : 'unknown'
    throw new ApiError(code, response.status)
  }
  return data
}
