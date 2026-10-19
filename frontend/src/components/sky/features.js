/**
 * What «Небосвод» lights: one star per feature on the vault (SkyVault) and one row in the
 * comparison (SkyCompare). The natal chart is free and always lit: the first star is already yours.
 */
export const FEATURES = [
  { id: 'chart', name: 'Натальная карта', free: 'целиком', sky: 'целиком', always: true },
  { id: 'day', name: 'Прогноз дня', free: 'первые строки', sky: 'полный текст каждый день' },
  { id: 'week', name: 'Прогноз недели', free: 'первые строки', sky: 'полный текст на семь дней' },
  { id: 'calendar', name: 'Звёздный календарь', free: 'семь дней вперёд', sky: 'тридцать дней и главный транзит дня' },
  { id: 'chat', name: 'Астролог', free: 'два вопроса', sky: 'без ограничений' },
  { id: 'pair', name: 'Разбор пары', free: 'сферы и первые строки', sky: 'полный разбор дешевле' },
]
