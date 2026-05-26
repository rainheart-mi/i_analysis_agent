<template>
  <div class="workflow-config">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="N8N环境" name="environments">
        <environment-list />
      </el-tab-pane>
      <el-tab-pane label="工作流路由" name="routes">
        <workflow-routes />
      </el-tab-pane>
      <el-tab-pane label="节点映射" name="mappings">
        <node-mappings />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import EnvironmentList from './EnvironmentList.vue'
import WorkflowRoutes from './WorkflowRoutes.vue'
import NodeMappings from './NodeMappings.vue'

const activeTab = ref('environments')
</script>

<style scoped>
.workflow-config {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
}
</style>