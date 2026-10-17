import { ref } from 'vue'

const items = ref([])
let nextId = 1

export function useToast() {
  function push(text) {
    const id = nextId++
    items.value = [...items.value, { id, text }]
    setTimeout(() => {
      items.value = items.value.filter((item) => item.id !== id)
    }, 4200)
  }

  return { items, push }
}
