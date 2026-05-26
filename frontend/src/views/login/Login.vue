<template>
  <div class="login-container">
    <!-- 背景装饰 -->
    <div class="bg-gradient"></div>
    <div class="bg-grid"></div>
    <div class="bg-glow"></div>

    <div class="login-card">
      <!-- Logo区域 -->
      <div class="logo-section">
        <div class="logo-icon">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="12" fill="url(#logoGrad)"/>
            <path d="M14 24h20M24 14v20" stroke="white" stroke-width="3" stroke-linecap="round"/>
            <defs>
              <linearGradient id="logoGrad" x1="0" y1="0" x2="48" y2="48">
                <stop stop-color="#667eea"/>
                <stop offset="1" stop-color="#764ba2"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h1 class="title">IERP</h1>
        <p class="subtitle">AI Assistant</p>
      </div>

      <!-- 登录表单 -->
      <el-form ref="formRef" :model="formData" :rules="rules" @submit.prevent="handleLogin" class="login-form">
        <el-form-item prop="username">
          <div class="input-wrapper">
            <span class="input-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="8" r="4"/>
                <path d="M4 20c0-4 4-6 8-6s8 2 8 6"/>
              </svg>
            </span>
            <el-input
              v-model="formData.username"
              placeholder="用户名"
              size="large"
              class="custom-input"
            />
          </div>
        </el-form-item>

        <el-form-item prop="password">
          <div class="input-wrapper">
            <span class="input-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="5" y="11" width="14" height="10" rx="2"/>
                <path d="M8 11V7a4 4 0 018 0v4"/>
              </svg>
            </span>
            <el-input
              v-model="formData.password"
              type="password"
              placeholder="密码"
              size="large"
              show-password
              class="custom-input"
              @keyup.enter="handleLogin"
            />
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="handleLogin"
            class="login-button"
          >
            <span v-if="!loading">登录</span>
            <span v-else class="loading-dots">
              <span></span><span></span><span></span>
            </span>
          </el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref(null)
const loading = ref(false)
const formData = ref({
  username: 'admin',
  password: 'admin123'
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    loading.value = true
    try {
      await userStore.login(formData.value.username, formData.value.password)
      ElMessage.success('登录成功')
      router.push('/')
    } catch (e) {
      ElMessage.error(e.message || '登录失败')
    } finally {
      loading.value = false
    }
  })
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #0a0a0f;
  position: relative;
  overflow: hidden;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* 背景装饰 */
.bg-gradient {
  position: absolute;
  width: 800px;
  height: 800px;
  top: -200px;
  right: -200px;
  background: radial-gradient(circle, rgba(102, 126, 234, 0.15) 0%, transparent 70%);
  animation: float 20s ease-in-out infinite;
}

.bg-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px);
  background-size: 60px 60px;
}

.bg-glow {
  position: absolute;
  width: 600px;
  height: 600px;
  bottom: -300px;
  left: -200px;
  background: radial-gradient(circle, rgba(118, 75, 162, 0.1) 0%, transparent 70%);
  animation: float 25s ease-in-out infinite reverse;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(30px, 20px) rotate(5deg); }
}

.login-card {
  width: 420px;
  padding: 48px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 24px;
  backdrop-filter: blur(20px);
  position: relative;
  z-index: 1;
  box-shadow:
    0 4px 24px rgba(0, 0, 0, 0.4),
    0 0 80px rgba(102, 126, 234, 0.1);
  animation: cardAppear 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes cardAppear {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.logo-section {
  text-align: center;
  margin-bottom: 40px;
  animation: fadeInDown 0.5s 0.1s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.logo-icon {
  margin-bottom: 16px;
  display: inline-block;
  animation: pulse 3s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.title {
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0 0 4px 0;
}

.subtitle {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 500;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin: 0;
}

.login-form {
  animation: fadeInUp 0.5s 0.2s cubic-bezier(0.16, 1, 0.3, 1) both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 16px;
  color: rgba(255, 255, 255, 0.3);
  z-index: 1;
  transition: color 0.3s;
}

.input-wrapper:focus-within .input-icon {
  color: #667eea;
}

:deep(.custom-input .el-input__wrapper) {
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  padding: 4px 16px 4px 44px !important;
  box-shadow: none !important;
  transition: all 0.3s !important;
}

:deep(.custom-input .el-input__wrapper:hover) {
  border-color: rgba(102, 126, 234, 0.5) !important;
}

:deep(.custom-input .el-input__wrapper.is-focus) {
  border-color: #667eea !important;
  background: rgba(102, 126, 234, 0.05) !important;
}

:deep(.custom-input .el-input__inner) {
  color: #fff !important;
  font-size: 15px !important;
}

:deep(.custom-input .el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.3) !important;
}

:deep(.custom-input .el-input__suffix) {
  color: rgba(255, 255, 255, 0.3) !important;
}

.login-button {
  width: 100%;
  height: 52px;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
  transition: all 0.3s !important;
  position: relative;
  overflow: hidden;
}

.login-button::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
  opacity: 0;
  transition: opacity 0.3s;
}

.login-button:hover::before {
  opacity: 1;
}

.login-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
}

.login-button:active {
  transform: translateY(0);
}

.login-button span {
  position: relative;
  z-index: 1;
}

.loading-dots {
  display: flex;
  gap: 4px;
  justify-content: center;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background: #fff;
  border-radius: 50%;
  animation: bounce 1.4s ease-in-out infinite;
}

.loading-dots span:nth-child(1) { animation-delay: 0s; }
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}
</style>