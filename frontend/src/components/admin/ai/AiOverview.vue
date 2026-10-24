<script setup>
import { computed } from 'vue'
import ColumnChart from '../ColumnChart.vue'
import { CATEGORIES, CATEGORY_TONE, SOURCES, SOURCE_NOTES, money, seconds } from '../../../views/admin/ai.js'
import { buckets, fmt, pct, stepOf } from '../../../views/admin/shared.js'

/**
 * How the ИИ-астролог is doing: the month's budget, the calls and their price, who answered the
 * people (the model, the templates, the service itself), what they ask about and why calls fail.
 */
const props = defineProps({
  data: { type: Object, required: true },
  days: { type: Number, required: true },
})
defineEmits(['open'])

const stats = computed(() => props.data.stats)
const value = (key) => props.data.settings.find((item) => item.key === key)?.value || ''
const keyFilled = computed(() => Boolean(props.data.settings.find((item) => item.key === 'ai_api_key')?.filled))
const mode = computed(() => value('ai_mode') || 'off')

const budget = computed(() => {
  const total = Number(props.data.budget || 0)
  const spent = Number(props.data.spent || 0)
  return { total, spent, share: total ? Math.min(1, spent / total) : 1, left: Math.max(0, total - spent) }
})
const monthName = new Intl.DateTimeFormat('ru-RU', { month: 'long', timeZone: 'Europe/Moscow' }).format(new Date())

const tiles = computed(() => {
  const s = stats.value
  return [
    { label: 'Вызовов модели', value: fmt.count(s.calls), hint: 'чат, песочница и проверки' },
    { label: 'Расход за срок', value: money(s.cost) },
    { label: 'Ответ в чате', value: s.per_answer ? money(s.per_answer) : '—', hint: 'в среднем, с повторами' },
    { label: 'Время ответа', value: seconds(s.ms), hint: 'в среднем у модели' },
    { label: 'Спрашивали', value: fmt.count(s.people), hint: 'человек' },
    { label: 'Ошибки', value: fmt.count(s.errors), hint: `отмечено проверкой: ${fmt.count(s.flagged)}`, bad: s.errors > 0 },
  ]
})

const cost = computed(() => buckets(stats.value.days, 'cost', props.days))
const answers = computed(() => buckets(stats.value.days, 'ai', props.days))

function bars(counts, names) {
  const rows = Object.entries(counts).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1])
  const total = rows.reduce((sum, [, n]) => sum + n, 0)
  const top = Math.max(1, ...rows.map(([, n]) => n))
  return rows.map(([key, n]) => ({ key, label: names[key] || key, n, share: pct(n, total), width: (n / top) * 100 }))
}
const sources = computed(() => bars(stats.value.sources, SOURCES))
const topics = computed(() => bars(stats.value.topics, CATEGORIES))
</script>

<template>
  <div class="ov">
    <section v-if="!data.ready" class="adm-panel ov-setup">
      <div class="adm-panel-head">
        <h2>Как подключить нейросеть</h2>
        <span class="adm-badge is-warn">пока отвечают шаблоны</span>
      </div>
      <ol class="ov-steps">
        <li>
          Войдите в <a href="https://console.yandex.cloud" target="_blank" rel="noopener">консоль Yandex Cloud</a>, привяжите платёжный аккаунт
          (оплата по счёту или российской картой) и создайте каталог. ID каталога — строка вида <code>b1g…</code> на его странице.
        </li>
        <li>В каталоге: «Сервисные аккаунты» → «Создать», роль <code>ai.languageModels.user</code>.</li>
        <li>Откройте аккаунт → «Создать новый ключ» → «API-ключ». Секрет покажут один раз — скопируйте его.</li>
        <li>Во вкладке «Настройки» вставьте ключ и ID каталога и нажмите «Проверить связь».</li>
        <li>Включите режим «Тест» со своей почтой, задайте вопросы в кабинете и прогоните «Провокации». Всё в порядке — режим «Включён».</li>
      </ol>
      <p class="ov-setup-state">
        <span class="adm-badge" :class="keyFilled ? 'is-ok' : 'is-plain'">ключ {{ keyFilled ? 'сохранён' : 'не задан' }}</span>
        <span class="adm-badge" :class="value('ai_folder') ? 'is-ok' : 'is-plain'">каталог {{ value('ai_folder') ? 'задан' : 'не задан' }}</span>
        <button type="button" class="adm-btn is-gold" @click="$emit('open', 'settings')">Открыть настройки</button>
      </p>
    </section>

    <section class="adm-panel ov-budget">
      <div class="adm-panel-head">
        <h2>Бюджет на {{ monthName }}</h2>
        <p>по московскому месяцу; с 1-го числа счёт заново</p>
      </div>
      <template v-if="budget.total">
        <div class="ov-meter" :class="{ 'is-over': budget.share >= 1, 'is-near': budget.share >= 0.8 && budget.share < 1 }">
          <i :style="{ width: `${budget.share * 100}%` }" />
        </div>
        <p class="ov-budget-line">
          <strong class="num">{{ money(budget.spent) }}</strong> из {{ fmt.rub(budget.total) }}
          <span class="adm-dim">· осталось {{ money(budget.left) }}</span>
        </p>
        <p v-if="budget.share >= 1" class="ov-warn">Бюджет исчерпан: до конца месяца отвечают шаблоны. Поднимите его в «Настройках», если нужно.</p>
        <p v-else-if="budget.share >= 0.8" class="ov-warn">Потрачено больше 80%: когда бюджет кончится, ответы перейдут на шаблоны.</p>
      </template>
      <p v-else class="ov-warn">Бюджет — 0 ₽: модель не вызывается. Задайте сумму в «Настройках».</p>
      <p v-if="mode === 'test'" class="adm-note ov-mode">Режим «Тест»: модель отвечает только тестировщикам.</p>
    </section>

    <div class="ov-tiles">
      <div v-for="tile in tiles" :key="tile.label" class="adm-panel ov-tile">
        <span class="ov-tile-label">{{ tile.label }}</span>
        <strong class="ov-tile-value num" :class="{ 'is-bad': tile.bad }">{{ tile.value }}</strong>
        <span v-if="tile.hint" class="ov-tile-hint">{{ tile.hint }}</span>
      </div>
    </div>

    <div class="ov-pair">
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Расход</h2>
          <p>₽ {{ stepOf(days) }}, все вызовы</p>
        </div>
        <ColumnChart :points="cost" name="Расход" color="#b8882c" :format="money" :axis-format="(v) => fmt.compact(v)" :height="200" />
      </section>
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Ответы модели в чате</h2>
          <p>{{ stepOf(days) }}</p>
        </div>
        <ColumnChart :points="answers" name="Ответов" color="#3987e5" :format="fmt.count" :axis-format="(v) => fmt.compact(v)" :height="200" />
      </section>
    </div>

    <div class="ov-pair">
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>Кто ответил людям</h2>
          <p>все ответы чата за срок</p>
        </div>
        <ul v-if="sources.length" class="ov-bars">
          <li v-for="row in sources" :key="row.key" :title="SOURCE_NOTES[row.key]">
            <span class="ov-bars-label">{{ row.label }}</span>
            <span class="ov-bars-track"><i :class="`is-${row.key}`" :style="{ width: `${row.width}%` }" /></span>
            <span class="ov-bars-value"><strong class="num">{{ fmt.count(row.n) }}</strong> · {{ row.share }}</span>
          </li>
        </ul>
        <p v-else class="adm-empty">За срок в чате не спрашивали</p>
        <p class="adm-note ov-legend">Модель — ответ нейросети, прошедший проверку. Шаблон — модель выключена, бюджет исчерпан или ответ не прошёл проверку. Ответ сервиса — код распознал кризис, попытку сменить роль или брань, модель не вызывалась.</p>
      </section>
      <section class="adm-panel">
        <div class="adm-panel-head">
          <h2>О чём спрашивают</h2>
          <p>как модель и код разметили вопросы</p>
        </div>
        <ul v-if="topics.length" class="ov-bars">
          <li v-for="row in topics" :key="row.key">
            <span class="ov-bars-label"><span class="adm-badge" :class="CATEGORY_TONE[row.key]">{{ row.label }}</span></span>
            <span class="ov-bars-track"><i :style="{ width: `${row.width}%` }" /></span>
            <span class="ov-bars-value"><strong class="num">{{ fmt.count(row.n) }}</strong> · {{ row.share }}</span>
          </li>
        </ul>
        <p v-else class="adm-empty">Вопросов за срок нет</p>
        <p class="adm-note ov-legend">«Не по теме», «попытка сменить роль» и «грубость» не списывают вопросы; три таких за полчаса — пауза 10 минут.</p>
      </section>
    </div>

    <section v-if="stats.reasons.length" class="adm-panel">
      <div class="adm-panel-head">
        <h2>Почему вызовы не удались</h2>
        <button type="button" class="text-button" @click="$emit('open', 'journal')">Журнал вызовов</button>
      </div>
      <ul class="ov-reasons">
        <li v-for="row in stats.reasons" :key="row.error">
          <span class="num">{{ fmt.count(row.n) }}×</span>
          <span>{{ row.error }}</span>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.ov { display: grid; gap: 18px; }
.ov-steps { display: grid; gap: 8px; margin: 0; padding-left: 1.3em; font-size: 15px; line-height: 1.5; }
.ov-steps a { color: var(--gold); }
.ov-steps code, .ov-setup code { font-size: 13.5px; padding: 1px 6px; border-radius: 6px; background: rgba(255, 240, 210, 0.07); }
.ov-setup-state { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; margin: 16px 0 0; }
.ov-setup-state .adm-btn { margin-left: auto; }

.ov-meter { height: 12px; border-radius: 999px; background: rgba(0, 0, 0, 0.3); border: 1px solid var(--panel-line); overflow: hidden; }
.ov-meter i { display: block; height: 100%; min-width: 4px; border-radius: 999px; background: var(--ok); transition: width 0.4s ease; }
.ov-meter.is-near i { background: var(--gold); }
.ov-meter.is-over i { background: var(--danger); }
.ov-budget-line { margin: 10px 0 0; font-size: 15px; }
.ov-budget-line strong { font-size: 20px; }
.ov-warn { margin: 8px 0 0; color: #e6c27a; font-size: 14px; }
.ov-mode { margin: 8px 0 0; }

.ov-tiles { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px; }
.ov-tile { display: grid; align-content: start; gap: 4px; padding: 14px 16px; }
.ov-tile-label { color: var(--muted); font-size: 13px; }
.ov-tile-value { font-size: 23px; font-weight: 600; line-height: 1.15; white-space: nowrap; }
.ov-tile-value.is-bad { color: var(--danger); }
.ov-tile-hint { color: var(--soft); font-size: 12px; }

.ov-pair { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }
.ov-bars { display: grid; gap: 12px; margin: 4px 0 0; padding: 0; list-style: none; }
.ov-bars li { display: grid; grid-template-columns: minmax(0, 190px) minmax(0, 1fr) auto; align-items: center; gap: 12px; }
.ov-bars-label { font-size: 15px; }
.ov-bars-track { display: block; height: 10px; }
.ov-bars-track i { display: block; height: 100%; min-width: 4px; border-radius: 0 4px 4px 0; background: var(--money); transition: width 0.3s ease; }
.ov-bars-track i.is-ai { background: var(--people); }
.ov-bars-track i.is-guard { background: var(--danger); }
.ov-bars-value { color: var(--soft); font-size: 13px; white-space: nowrap; }
.ov-bars-value strong { color: var(--ink); font-size: 14px; }
.ov-legend { margin: 16px 0 0; font-size: 13px; }

.ov-reasons { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; font-size: 14px; }
.ov-reasons li { display: grid; grid-template-columns: 48px minmax(0, 1fr); gap: 10px; }
.ov-reasons .num { color: var(--danger); font-weight: 600; }

@media (max-width: 1200px) {
  .ov-tiles { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 1000px) {
  .ov-pair { grid-template-columns: minmax(0, 1fr); }
}
@media (max-width: 640px) {
  .ov-tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .ov-tile-value { font-size: 20px; }
  .ov-bars li { grid-template-columns: minmax(0, 1fr) auto; }
  .ov-bars-track { grid-column: 1 / -1; grid-row: 2; }
  .ov-setup-state .adm-btn { margin-left: 0; }
}
</style>
