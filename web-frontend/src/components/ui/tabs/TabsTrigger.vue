<script setup>
import { inject, computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  value: String,
  disabled: Boolean,
  class: String
})

const activeTab = inject('activeTab')
const setTab = inject('setTab')

const isActive = computed(() => activeTab?.value === props.value)

const triggerClass = computed(() => cn(
  'inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  isActive.value && 'bg-background text-foreground shadow-sm',
  props.class
))
</script>

<template>
  <button
    :class="triggerClass"
    :disabled="disabled"
    @click="!disabled && setTab(value)"
  >
    <slot />
  </button>
</template>
