<template>
  <div class="workflow-selector">
    <el-select
      v-model="selectedId"
      placeholder="请选择工作流"
      filterable
      @change="handleChange"
    >
      <el-option-group
        v-for="group in groupedWorkflows"
        :key="group.label"
        :label="group.label"
      >
        <el-option
          v-for="wf in group.options"
          :key="wf.id"
          :label="wf.title"
          :value="wf.id"
        >
          <div class="workflow-option-content">
            <div class="workflow-title">{{ wf.title }}</div>
            <div class="workflow-desc">{{ wf.description }}</div>
          </div>
        </el-option>
      </el-option-group>
    </el-select>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  workflows: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['change'])

const selectedId = ref(null)

const groupedWorkflows = computed(() => {
  const active = props.workflows.filter(w => w.is_active)
  return [
    {
      label: '可用工作流',
      options: active
    }
  ]
})

const handleChange = (workflowId) => {
  const workflow = props.workflows.find(w => w.id === workflowId)
  emit('change', workflow)
}
</script>

<style scoped>
.workflow-option-content {
  padding: 4px 0;
}

.workflow-title {
  font-weight: 500;
}

.workflow-desc {
  font-size: 0.8rem;
  color: #94a3b8;
}
</style>