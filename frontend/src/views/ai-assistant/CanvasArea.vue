<template>
  <div class="canvas-area">
    <!-- 空状态 -->
    <div v-if="!workflow" class="empty-state">
      <div class="empty-card">
        <div class="empty-icon">
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="url(#emptyGrad)" stroke-width="2" stroke-dasharray="6 4"/>
            <path d="M24 28h16M24 36h10" stroke="#667eea" stroke-width="2" stroke-linecap="round"/>
            <defs>
              <linearGradient id="emptyGrad" x1="0" y1="0" x2="64" y2="64">
                <stop stop-color="#667eea"/>
                <stop offset="1" stop-color="#764ba2"/>
              </linearGradient>
            </defs>
          </svg>
        </div>
        <h3>选择一个工作流开始分析</h3>
        <p>从右侧面板选择工作流，系统将为您构建分析表单</p>
      </div>
    </div>

    <!-- 意图澄清表单 -->
    <template v-else-if="intentSchema && !executionResult">
      <div class="cards-row">
        <div class="form-card">
          <div class="card-header">
            <div class="header-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="18" height="18" rx="3" stroke="currentColor" stroke-width="2"/>
                <path d="M9 9h6M9 13h4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </div>
            <div class="header-text">
              <h2>{{ workflow.title }}</h2>
              <p>{{ workflow.description }}</p>
            </div>
          </div>
          <div class="card-body">
            <dynamic-form
              ref="intentFormRef"
              :schema="intentSchema"
              v-model="intentFormData"
            />
          </div>
          <div class="card-footer">
            <el-button @click="handleReset" class="btn-reset">重置</el-button>
            <el-button type="primary" @click="handleSubmit" class="btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13 5l7 7-7 7M5 12h15"/>
              </svg>
              执行工作流
            </el-button>
          </div>
        </div>
        <div class="guide-card">
          <div class="guide-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              <path d="M12 16v-4M12 8h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span>填写指南</span>
          </div>
          <ul class="guide-list">
            <li>选择分析的大类和时间范围</li>
            <li>支持按门店和品类筛选</li>
            <li>设置完成后点击执行工作流</li>
          </ul>
          <div class="guide-tips">
            <div class="tip-item">
              <span class="tip-dot green"></span>
              <span>销售达成率 ≥100% 为优秀</span>
            </div>
            <div class="tip-item">
              <span class="tip-dot yellow"></span>
              <span>80% ≤ 达成率 &lt;100% 为正常</span>
            </div>
            <div class="tip-item">
              <span class="tip-dot red"></span>
              <span>达成率 &lt;80% 需关注</span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 生成物表单预览 -->
    <template v-else-if="executionResult && artifactSchema">
      <div class="cards-row">
        <div class="form-card result-card">
          <div class="card-header">
            <div class="header-icon success">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
                <path d="M8 12l3 3 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="header-text">
              <h2>执行结果</h2>
              <p>工作流执行完成，以下是生成的数据</p>
            </div>
          </div>
          <div class="card-body">
            <dynamic-form
              :schema="artifactSchema"
              :model-value="artifactFormData"
              readonly
            />
          </div>
          <div class="card-footer">
            <el-button @click="handleBack" class="btn-reset">返回表单</el-button>
            <el-button type="primary" class="btn-primary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/>
              </svg>
              导出结果
            </el-button>
          </div>
        </div>
        <div class="guide-card success">
          <div class="guide-header">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              <path d="M22 4L12 14.01l-3-3" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span>数据洞察</span>
          </div>
          <ul class="guide-list">
            <li>点击大类名称可下钻到商品明细</li>
            <li>销售达成率100%以上为绿色</li>
            <li>80-100%为黄色，80%以下为红色</li>
            <li>周环比：上升箭头绿色，下降红色</li>
          </ul>
        </div>
      </div>
    </template>

    <!-- 执行中状态 -->
    <template v-else-if="isExecuting">
      <div class="loading-card">
        <div class="loader">
          <div class="loader-ring"></div>
          <div class="loader-icon">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" stroke="#667eea" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
        </div>
        <h3>工作流执行中</h3>
        <p>正在处理您的请求，请稍候...</p>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import DynamicForm from './DynamicForm.vue'

const props = defineProps({
  workflow: Object,
  intentSchema: Object,
  artifactSchema: Object,
  executionResult: Object
})

const emit = defineEmits(['submit'])

const intentFormRef = ref(null)
const intentFormData = ref({})
const artifactFormData = ref({})
const isExecuting = ref(false)

watch(
  () => props.artifactSchema,
  (schema) => {
    if (schema) {
      artifactFormData.value = { ...props.executionResult }
    }
  }
)

const handleSubmit = () => {
  isExecuting.value = true
  emit('submit', intentFormData.value)
}

const handleReset = () => {
  intentFormData.value = {}
}

const handleBack = () => {
  intentFormData.value = {}
  artifactFormData.value = {}
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

.canvas-area {
  height: 100%;
  overflow-y: auto;
  padding: 24px;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  background: linear-gradient(135deg, #f8f9fb 0%, #f0f2f5 100%);
}

/* Empty State Card */
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-card {
  text-align: center;
  padding: 48px;
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
  max-width: 400px;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.empty-icon {
  margin-bottom: 24px;
  opacity: 0.8;
}

.empty-card h3 {
  margin: 0 0 8px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a1a2e;
}

.empty-card p {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
}

/* Cards Row - Left to Right Layout */
.cards-row {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 20px;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Form Card */
.form-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.result-card {
  border-top: 3px solid #10B981;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 24px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.04) 0%, rgba(118, 75, 162, 0.04) 100%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}

.header-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(102, 126, 234, 0.1);
  color: #667eea;
  flex-shrink: 0;
}

.header-icon.success {
  background: rgba(16, 185, 129, 0.1);
  color: #10B981;
}

.header-text h2 {
  margin: 0 0 4px 0;
  font-size: 1.2rem;
  font-weight: 700;
  color: #1a1a2e;
}

.header-text p {
  margin: 0;
  font-size: 0.85rem;
  color: #64748b;
}

.card-body {
  padding: 24px;
}

.card-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 20px 24px;
  background: #fafafa;
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

.btn-reset {
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #fff;
  color: #64748b;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-reset:hover {
  border-color: #667eea;
  color: #667eea;
}

.btn-primary {
  padding: 10px 24px;
  border-radius: 10px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: #fff;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.35);
}

.btn-primary svg {
  width: 16px;
  height: 16px;
}

/* Guide Card */
.guide-card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
  border: 1px solid rgba(0, 0, 0, 0.04);
  overflow: hidden;
  height: fit-content;
  position: sticky;
  top: 24px;
}

.guide-card.success {
  border-top: 3px solid #10B981;
}

.guide-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%);
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  color: #667eea;
  font-weight: 600;
  font-size: 0.9rem;
}

.guide-card.success .guide-header {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.06) 0%, rgba(16, 185, 129, 0.06) 100%);
  color: #10B981;
}

.guide-list {
  list-style: none;
  margin: 0;
  padding: 16px 20px;
}

.guide-list li {
  position: relative;
  padding-left: 16px;
  margin-bottom: 12px;
  font-size: 0.85rem;
  color: #64748b;
  line-height: 1.5;
}

.guide-list li::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.guide-card.success .guide-list li::before {
  background: #10B981;
}

.guide-list li:last-child {
  margin-bottom: 0;
}

.guide-tips {
  padding: 12px 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tip-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.8rem;
  color: #64748b;
}

.tip-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.tip-dot.green { background: #10B981; }
.tip-dot.yellow { background: #F59E0B; }
.tip-dot.red { background: #EF4444; }

/* Loading Card */
.loading-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.06);
  border: 1px solid rgba(0, 0, 0, 0.04);
  padding: 48px;
  text-align: center;
  animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

.loader {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 24px;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #667eea;
  animation: spin 1s linear infinite;
}

.loader-ring::before {
  content: '';
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  border: 3px solid transparent;
  border-top-color: #764ba2;
  animation: spin 0.8s linear infinite reverse;
}

.loader-icon {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: spin 2s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-card h3 {
  margin: 0 0 8px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a1a2e;
}

.loading-card p {
  margin: 0;
  font-size: 0.85rem;
  color: #94a3b8;
}

/* Animations */
@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>