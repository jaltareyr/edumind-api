import { apiRequest } from './http'

export const signIn = async ({ username, password }) => {
  if (!username || !password) {
    throw new Error('Username and password are required')
  }
  return apiRequest('/auth/login', {
    method: 'POST',
    body: { username, password },
  })
}

export const signOut = async () => {
  await apiRequest('/auth/logout', { method: 'POST' })
}

export const fetchCurrentUser = async () => {
  return apiRequest('/auth/me')
}
