import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { registerPlugins } from './plugins'
import './style.css'
import { useUserStore } from '@/stores'

const pinia = createPinia()

const bootstrap = async () => {
  const app = createApp(App)
  registerPlugins(app)

  app.use(pinia)
  app.use(router)

  const userStore = useUserStore()
  await userStore.hydrate()

  app.mount('#app')
}

bootstrap()
