<script setup>
/** A modal question before an action that is hard to undo; `need` is a word to type in first. */
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  text: { type: String, default: '' },
  label: { type: String, default: 'Подтвердить' },
  need: { type: String, default: '' },
  busy: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
const emit = defineEmits(['confirm', 'cancel'])

const dialog = ref(null)
const typed = ref('')
const ready = computed(() => !props.need || typed.value.trim().toLowerCase() === props.need.toLowerCase())

watch(
  () => props.open,
  async (open) => {
    await nextTick()
    if (open) {
      typed.value = ''
      if (!dialog.value.open) dialog.value.showModal()
    } else if (dialog.value?.open) {
      dialog.value.close()
    }
  },
)
</script>

<template>
  <dialog ref="dialog" class="cd" @cancel.prevent="emit('cancel')" @click.self="emit('cancel')">
    <form class="cd-body" @submit.prevent="ready && emit('confirm', typed.trim())">
      <h2>{{ title }}</h2>
      <p>{{ text }}</p>
      <label v-if="need" class="adm-label">
        Для подтверждения введите {{ need }}
        <input v-model="typed" type="text" autocomplete="off" spellcheck="false" />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="adm-actions cd-actions">
        <button type="button" class="adm-btn" @click="emit('cancel')">Отмена</button>
        <button type="submit" class="adm-btn is-danger is-solid" :disabled="!ready || busy">{{ busy ? 'Минутку…' : label }}</button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
.cd {
  width: min(440px, calc(100% - 32px));
  padding: 0;
  border: 1px solid rgba(244, 239, 230, 0.14);
  border-radius: 20px;
  background: #141c19;
  color: var(--ink);
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.5);
}
.cd::backdrop { background: rgba(4, 6, 10, 0.6); }
.cd-body { display: grid; gap: 12px; padding: 22px; }
.cd h2 { margin: 0; font-family: var(--sans); font-size: 19px; font-weight: 600; letter-spacing: 0; }
.cd p { margin: 0; color: var(--muted); font-size: 15px; }
.cd input { font-size: 15px; padding: 10px 12px; }
.cd-actions { justify-content: flex-end; margin-top: 6px; }
</style>
