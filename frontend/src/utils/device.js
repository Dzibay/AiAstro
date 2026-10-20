/**
 * Phones, tablets and modest machines get the light sky: a cheaper shader, no live glass,
 * and a sky that does not follow the scroll. Decided once, at start, and marked on <html>
 * as `.lite`, so the styles can follow too.
 */
function detect() {
  if (typeof window === 'undefined') return false
  const touch = window.matchMedia('(hover: none) and (pointer: coarse)').matches
  const cores = navigator.hardwareConcurrency || 8
  const memory = navigator.deviceMemory || 8
  return touch || window.innerWidth < 760 || cores <= 4 || memory <= 4 || Boolean(navigator.connection?.saveData)
}

export const LITE = detect()

export function markDevice() {
  document.documentElement.classList.toggle('lite', LITE)
}
