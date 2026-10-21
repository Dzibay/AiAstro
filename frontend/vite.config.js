import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: Number(process.env.PORT) || 5173,
    proxy: {
      // API_TARGET points a second dev server at another backend, e.g. a test one.
      '/api': process.env.API_TARGET || 'http://127.0.0.1:8000',
    },
  },
})
