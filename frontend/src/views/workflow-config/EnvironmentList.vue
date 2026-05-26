<template>
  <div class="environment-list">
    <div class="toolbar">
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建环境
      </el-button>
    </div>

    <el-table :data="environments" v-loading="loading">
      <el-table-column prop="name" label="环境名称" />
      <el-table-column prop="base_url" label="N8N地址" />
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '激活' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="primary" @click="handleTest(row)">测试</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
      <el-form :model="formData" label-width="100px">
        <el-form-item label="环境名称">
          <el-input v-model="formData.name" />
        </el-form-item>
        <el-form-item label="N8N地址">
          <el-input v-model="formData.base_url" placeholder="http://localhost:5678" />
        </el-form-item>
        <el-form-item label="API Key">
          <el-input v-model="formData.api_key" show-password />
        </el-form-item>
        <el-form-item label="激活状态">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { workflowApi } from '@/api/workflow'

const environments = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formData = ref({
  name: '',
  base_url: '',
  api_key: '',
  is_active: true
})

onMounted(() => {
  fetchEnvironments()
})

const fetchEnvironments = async () => {
  loading.value = true
  try {
    const res = await workflowApi.getEnvironments()
    environments.value = res.data
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  formData.value = { name: '', base_url: '', api_key: '', is_active: true }
  dialogTitle.value = '新建环境'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  formData.value = { ...row }
  dialogTitle.value = '编辑环境'
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (formData.value.id) {
      await workflowApi.updateEnvironment(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await workflowApi.createEnvironment(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchEnvironments()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleTest = async (row) => {
  try {
    const res = await workflowApi.testEnvironment(row.id)
    if (res.data.success) {
      ElMessage.success('连接成功')
    } else {
      ElMessage.error(res.data.message)
    }
  } catch (e) {
    ElMessage.error('连接失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该环境吗？', '警告', { type: 'warning' })
    await workflowApi.deleteEnvironment(row.id)
    ElMessage.success('删除成功')
    fetchEnvironments()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>