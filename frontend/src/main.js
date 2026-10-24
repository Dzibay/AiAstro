import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import { markDevice } from './utils/device.js'
import { installFaults } from './utils/faults.js'
import { watchQuality } from './utils/quality.js'
import { installTracking, vSeen } from './utils/track.js'
import './styles/site.css'
import './styles/book.css'

markDevice()
watchQuality()
installTracking(router)
const app = createApp(App).use(router).directive('seen', vSeen)
installFaults(app, router)
app.mount('#app')
