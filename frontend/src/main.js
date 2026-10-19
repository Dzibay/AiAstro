import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import './styles/site.css'
import './styles/book.css'

createApp(App).use(router).mount('#app')
