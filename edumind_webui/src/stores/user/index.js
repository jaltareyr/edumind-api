import { defineStore } from 'pinia'
import { fetchCurrentUser, signIn as loginRequest, signOut as logoutRequest } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    loading: false,
    error: null,
    hydrated: false,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user),
    userId: (state) => state.user?.id || '',
    displayName: (state) => state.user?.full_name || '',
    role: (state) => state.user?.role || 'guest',
  },
  actions: {
    async hydrate() {
      if (this.hydrated || this.loading) {
        return
      }
      this.loading = true
      try {
        const response = await fetchCurrentUser()
        this.user = response?.user || null
        this.error = null
      } catch (error) {
        this.user = null
        this.error = null
      } finally {
        this.hydrated = true
        this.loading = false
      }
    },
    async signIn({ username, password }) {
      const payload = {
        username: (username || '').trim(),
        password: password || '',
      }
      this.loading = true
      this.error = null
      try {
        const response = await loginRequest(payload)
        this.user = response?.user || null
        this.hydrated = true
        return this.user
      } catch (error) {
        this.error = error
        this.user = null
        throw error
      } finally {
        this.loading = false
      }
    },
    async signOut() {
      try {
        await logoutRequest()
      } finally {
        this.user = null
        this.hydrated = true
        this.error = null
      }
    },
  },
})
