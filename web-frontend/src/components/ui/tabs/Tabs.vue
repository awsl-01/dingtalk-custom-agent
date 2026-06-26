<script setup>
import { ref, provide } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: String,
  class: String
})

const emit = defineEmits(['update:modelValue'])

const activeTab = ref(props.modelValue)

provide('activeTab', activeTab)
provide('setTab', (value) => {
  activeTab.value = value
  emit('update:modelValue', value)
  emit('change', value)
})

const tabsClass = cn('w-full', props.class)
</script>

<template>
  <div :class="tabsClass">
    <slot />
  </div>
</template>
