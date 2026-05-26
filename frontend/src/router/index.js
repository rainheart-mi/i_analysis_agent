import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Login.vue')
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Dashboard.vue')
      },
      {
        path: 'workflow-config',
        name: 'WorkflowConfig',
        component: () => import('@/views/workflow-config/index.vue')
      },
      {
        path: 'ai-assistant',
        name: 'AIAssistant',
        component: () => import('@/views/ai-assistant/AIAssistant.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router