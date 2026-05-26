<template>
  <div class="workflow-routes">
    <div class="toolbar">
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        新建工作流
      </el-button>
    </div>

    <el-table :data="workflows" v-loading="loading">
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="description" label="描述" show-overflow-tooltip />
      <el-table-column prop="n8n_workflow_id" label="N8N工作流ID" />
      <el-table-column prop="is_active" label="状态">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
            {{ row.is_active ? '激活' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="formData" label-width="120px">
        <el-form-item label="所属环境">
          <el-select v-model="formData.environment_id" placeholder="请选择">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="formData.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="formData.description" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="N8N工作流ID">
          <el-input v-model="formData.n8n_workflow_id" />
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

const workflows = ref([])
const environments = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formData = ref({
  environment_id: '',
  title: '',
  description: '',
  n8n_workflow_id: '',
  is_active: true
})

onMounted(() => {
  fetchData()
})

const fetchData = async () => {
  loading.value = true
  try {
    const [wfRes, envRes] = await Promise.all([
      workflowApi.getWorkflows(),
      workflowApi.getEnvironments()
    ])
    workflows.value = wfRes.data.items
    environments.value = envRes.data
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  formData.value = { environment_id: '', title: '', description: '', n8n_workflow_id: '', is_active: true }
  dialogTitle.value = '新建工作流'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  formData.value = { ...row }
  dialogTitle.value = '编辑工作流'
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (formData.value.id) {
      await workflowApi.updateWorkflow(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await workflowApi.createWorkflow(formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该工作流吗？', '警告', { type: 'warning' })
    await workflowApi.deleteWorkflow(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>