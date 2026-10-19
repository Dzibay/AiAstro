<script setup>
import BirthForm from '../../components/cabinet/BirthForm.vue'

/** The birth data, opened from the person's star or the overview. CabinetView leads back. */

defineProps({
  user: { type: Object, required: true },
})
const emit = defineEmits(['saved', 'done'])
</script>

<template>
  <BirthForm :birth="user.birth" @saved="emit('saved', $event)" @cancel="emit('done')" />
</template>
