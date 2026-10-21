import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import { markDevice } from './utils/device.js'
import { watchQuality } from './utils/quality.js'
import { installTracking } from './utils/track.js'
import './styles/site.css'
import './styles/book.css'

markDevice()
watchQuality()
installTracking(router)
createApp(App).use(router).mount('#app')
