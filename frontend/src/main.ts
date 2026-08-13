import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import AdminApp from './admin/AdminApp.vue'
import './style.css'
import './styles/compare.css'
import './admin/admin.css'
import './admin/admin-components.css'
import './styles/mobile-scroll-admin.css'

const RootApp = window.location.pathname.startsWith('/admin') ? AdminApp : App

createApp(RootApp).use(ElementPlus).mount('#app')
