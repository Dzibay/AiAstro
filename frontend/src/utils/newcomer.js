import { addMark, hasMark } from './marks.js'

/**
 * The steps of «Путь новичка» that leave no other trace on the server: the Sun read, a question
 * asked. Kept in the account (utils/marks.js), so the checklist remembers them on any device.
 */

export function markStep(userId, step) {
  addMark(userId, `step:${step}`)
}

export const stepDone = (userId, step) => hasMark(userId, `step:${step}`)
