import request from './request'

export function loginApi(username, password) {
  return request.post('/auth/login', { username, password })
}

export function getMeApi() {
  return request.get('/auth/me')
}

export function logoutApi() {
  return request.post('/auth/logout')
}
