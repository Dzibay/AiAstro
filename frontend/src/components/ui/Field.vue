<script setup>
defineProps({
  label: { type: String, required: true },
  modelValue: { type: String, default: '' },
  type: { type: String, default: 'text' },
  autocomplete: { type: String, default: 'on' },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <label class="field">
    <span>{{ label }}</span>
    <input
      :type="type"
      :value="modelValue"
      :autocomplete="autocomplete"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  </label>
</template>
