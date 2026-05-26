import { defineStore } from 'pinia'
import { authApi } from '@/api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    user: null,
    accessToken: localStorage.getItem('access_token'),
    refreshToken: localStorage.getItem('refresh_token')
  }),

  getters: {
    isLoggedIn: (state) => !!state.accessToken
  },

  actions: {
    async login(username, password) {
      const res = await authApi.login(username, password)
      this.accessToken = res.data.access_token
      this.refreshToken = res.data.refresh_token
      localStorage.setItem('access_token', res.data.access_token)
      localStorage.setItem('refresh_token', res.data.refresh_token)
      await this.fetchCurrentUser()
    },

    async fetchCurrentUser() {
      try {
        const res = await authApi.getCurrentUser()
        this.user = res.data
      } catch (e) {
        this.logout()
      }
    },

    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
    }
  }
})