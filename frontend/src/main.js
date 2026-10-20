import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import { markDevice } from './utils/device.js'
import './styles/site.css'
import './styles/book.css'

markDevice()
createApp(App).use(router).mount('#app')
