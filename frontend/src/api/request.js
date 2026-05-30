import axios from 'axios'
import { useUserStore } from '../store/user'
import router from '../router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const userStore = useUserStore()
  if (userStore.token) {
    config.headers.Authorization = `Bearer ${userStore.token}`
  }
  // Ensure Content-Type is set for JSON requests
  if (!config.headers['Content-Type'] && config.data && typeof config.data === 'object') {
    config.headers['Content-Type'] = 'application/json'
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default request
