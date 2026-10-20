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
  consent: 'Нужно согласие на обработку персональных данных',
  birth: 'Проверьте дату рождения',
  place: 'Выберите город из подсказок или сотрите координаты',
  no_birth: 'Сначала укажите дату рождения',
  places: 'Подсказки городов сейчас недоступны',
  busy: 'Слишком много запросов, попробуйте через минуту',
  setting: 'Эту настройку нельзя сохранить',
  missing: 'Такой страницы нет',
  name: 'Укажите имя',
  partners_limit: 'Пар уже двадцать — удалите одну, чтобы добавить новую',
  pending: 'Партнёр ещё не ответил на приглашение',
  filled: 'Эта звезда уже зажглась',
  question: 'Напишите вопрос',
  question_long: 'Вопрос слишком длинный — сократите его до 600 знаков',
  trial_over: 'Пробные вопросы закончились',
  wrong_password: 'Неверный пароль',
  pay_off: 'Оплата пока не подключена',
  price: 'Цена ещё не назначена',
  bought: 'Этот разбор уже открыт',
  pay_failed: 'Платёжный сервис не ответил, попробуйте ещё раз',
  product: 'Такого тарифа нет',
  mail_off: 'Письма пока не отправляются — напишите в поддержку',
  reset: 'Ссылка устарела или уже открывалась — попросите новую',
  birth_locked: 'Данные рождения уже исправлялись — следующую правку внесёт поддержка',
  partner_locked: 'Данные этого партнёра уже нельзя изменить',
  linked: 'Это приглашение уже принято другим кабинетом',
  self: 'Это ваше собственное приглашение',
  claim: 'Не получилось присоединить пару — откройте приглашение ещё раз',
  state: 'Такого фильтра нет',
  confirm: 'Почта не совпадает — аккаунт не удалён',
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
