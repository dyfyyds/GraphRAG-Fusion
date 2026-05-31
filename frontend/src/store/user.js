import { defineStore } from 'pinia'
import { ref } from 'vue'
import { loginApi, registerApi, getMeApi } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(null)

  async function login(username, password) {
    const data = await loginApi(username, password)
    await applyToken(data.access_token)
  }

  async function register(username, password, email) {
    const data = await registerApi(username, password, email)
    await applyToken(data.access_token)
  }

  async function applyToken(accessToken) {
    token.value = accessToken
    localStorage.setItem('token', accessToken)
    await fetchUser()
  }

  async function fetchUser() {
    try {
      userInfo.value = await getMeApi()
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
  }

  return { token, userInfo, login, register, fetchUser, logout }
})
