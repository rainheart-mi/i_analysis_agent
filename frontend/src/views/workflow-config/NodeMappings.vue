<template>
  <div class="node-mappings">
    <div class="toolbar">
      <el-select v-model="selectedRouteId" placeholder="选择工作流" @change="fetchMappings">
        <el-option
          v-for="wf in workflows"
          :key="wf.id"
          :label="wf.title"
          :value="wf.id"
        />
      </el-select>
      <el-button type="primary" @click="handleCreate" :disabled="!selectedRouteId">
        <el-icon><Plus /></el-icon>
        新建映射
      </el-button>
    </div>

    <el-table :data="mappings" v-loading="loading">
      <el-table-column prop="node_id" label="节点ID" />
      <el-table-column prop="node_name" label="节点名称" />
      <el-table-column prop="intent_schema_path" label="意图表单路径" show-overflow-tooltip />
      <el-table-column prop="artifact_schema_path" label="生成物表单路径" show-overflow-tooltip />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
          <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="formData" label-width="140px">
        <el-form-item label="节点ID">
          <el-input v-model="formData.node_id" />
        </el-form-item>
        <el-form-item label="节点名称">
          <el-input v-model="formData.node_name" />
        </el-form-item>
        <el-form-item label="意图表单Schema路径">
          <el-input v-model="formData.intent_schema_path" placeholder="intent_forms/{route_id}/intent_schema.json" />
        </el-form-item>
        <el-form-item label="生成物表单Schema路径">
          <el-input v-model="formData.artifact_schema_path" placeholder="artifact_forms/{route_id}/artifact_schema.json" />
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
const mappings = ref([])
const selectedRouteId = ref(null)
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formData = ref({
  node_id: '',
  node_name: '',
  intent_schema_path: '',
  artifact_schema_path: ''
})

onMounted(() => {
  fetchWorkflows()
})

const fetchWorkflows = async () => {
  const res = await workflowApi.getWorkflows()
  workflows.value = res.data.items
}

const fetchMappings = async () => {
  if (!selectedRouteId.value) return
  loading.value = true
  try {
    const res = await workflowApi.getMappings(selectedRouteId.value)
    mappings.value = res.data.items
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  formData.value = { node_id: '', node_name: '', intent_schema_path: '', artifact_schema_path: '' }
  dialogTitle.value = '新建映射'
  dialogVisible.value = true
}

const handleEdit = (row) => {
  formData.value = { ...row }
  dialogTitle.value = '编辑映射'
  dialogVisible.value = true
}

const handleSave = async () => {
  try {
    if (formData.value.id) {
      await workflowApi.updateMapping(formData.value.id, formData.value)
      ElMessage.success('更新成功')
    } else {
      await workflowApi.createMapping(selectedRouteId.value, formData.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchMappings()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除该映射吗？', '警告', { type: 'warning' })
    await workflowApi.deleteMapping(row.id)
    ElMessage.success('删除成功')
    fetchMappings()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 12px;
}
</style>