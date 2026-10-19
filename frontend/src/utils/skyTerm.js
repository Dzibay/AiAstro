/** The term of «Небосвод» in words: «горит до 12 ноября, ещё 23 дня». */

const untilFormat = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long' })

export function daysWord(n) {
  const tens = n % 100
  const ones = n % 10
  if (tens > 10 && tens < 20) return 'дней'
  if (ones === 1) return 'день'
  return ones > 1 && ones < 5 ? 'дня' : 'дней'
}

export function skyDaysLeft(user) {
  if (!user?.sky || !user.sky_until) return 0
  return Math.max(0, Math.ceil((new Date(user.sky_until) - Date.now()) / 86400000))
}

export function skyLine(user) {
  if (!user?.sky) return 'пока не зажжён'
  const left = skyDaysLeft(user)
  const until = untilFormat.format(new Date(user.sky_until))
  return `горит до ${until}, ${left === 0 ? 'последний день' : `ещё ${left} ${daysWord(left)}`}`
}

/** The last few days: the renewal comes forward. */
export function skyEnding(user) {
  return Boolean(user?.sky) && skyDaysLeft(user) <= 5
}
