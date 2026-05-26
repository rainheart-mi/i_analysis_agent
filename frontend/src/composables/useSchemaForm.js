import { ref, computed } from 'vue'
import { parseSchema } from '@/utils/schemaParser'

export function useSchemaForm(schemaRef) {
  const formData = ref({})
  const formRules = ref({})

  const formItems = computed(() => {
    if (!schemaRef.value) return []
    return parseSchema(schemaRef.value)
  })

  const initFormData = (data = {}) => {
    const initial = {}
    formItems.value.forEach(item => {
      if (item.config?.default !== undefined) {
        initial[item.prop] = item.config.default
      }
    })
    formData.value = { ...initial, ...data }
  }

  const validate = () => {
    // Basic validation logic
    return true
  }

  const getSubmitData = () => {
    return { ...formData.value }
  }

  return {
    formData,
    formRules,
    formItems,
    initFormData,
    validate,
    getSubmitData
  }
}