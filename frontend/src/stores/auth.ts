import { defineStore } from 'pinia'
import { login as apiLogin, checkAuth as apiCheckAuth } from '../api'

export interface AuthState {
  isAuthenticated: boolean
  isLoading: boolean
}

const AUTH_TOKEN_KEY = 'auth-token'

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    isAuthenticated: false,
    isLoading: true
  }),

  actions: {
    async checkAuth() {
      const token = localStorage.getItem(AUTH_TOKEN_KEY)
      if (!token) {
        this.isAuthenticated = false
        this.isLoading = false
        return false
      }

      try {
        const result = await apiCheckAuth(token)
        this.isAuthenticated = result.valid
        if (!result.valid) {
          localStorage.removeItem(AUTH_TOKEN_KEY)
        }
      } catch {
        this.isAuthenticated = false
        localStorage.removeItem(AUTH_TOKEN_KEY)
      } finally {
        this.isLoading = false
      }
      return this.isAuthenticated
    },

    async login(password: string): Promise<{ success: boolean; error?: string }> {
      try {
        const result = await apiLogin(password)
        if (result.success && result.token) {
          localStorage.setItem(AUTH_TOKEN_KEY, result.token)
          this.isAuthenticated = true
          return { success: true }
        }
        return { success: false, error: result.error || '密码错误' }
      } catch (error) {
        return { success: false, error: '登录失败，请稍后重试' }
      }
    },

    logout() {
      localStorage.removeItem(AUTH_TOKEN_KEY)
      this.isAuthenticated = false
    },

    getToken(): string | null {
      return localStorage.getItem(AUTH_TOKEN_KEY)
    }
  }
})
