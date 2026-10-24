import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  build: {
    // three.js (~530 kB, 140 kB gzip) comes only with the natal sky game and only when it opens.
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        // The libraries in files of their own: a release of the site's code leaves them in the browser's cache.
        manualChunks(id) {
          if (id.includes('/node_modules/three/')) return 'three'
          if (/\/node_modules\/(@vue|vue|vue-router)\//.test(id)) return 'vue'
          return undefined
        },
      },
    },
  },
  server: {
    host: '127.0.0.1',
    port: Number(process.env.PORT) || 5173,
    proxy: {
      // API_TARGET points a second dev server at another backend, e.g. a test one.
      '/api': process.env.API_TARGET || 'http://127.0.0.1:8000',
    },
  },
})
