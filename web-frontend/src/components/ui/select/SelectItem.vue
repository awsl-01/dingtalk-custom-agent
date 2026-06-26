<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { Check } from 'lucide-vue-next'

const props = defineProps({
  value: [String, Number],
  disabled: Boolean,
  class: String
})

const isSelected = computed(() => {
  // 需要从父组件获取选中值
  return false
})

const itemClass = computed(() => cn(
  'relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-8 pr-2 text-sm outline-none hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
  props.class
))
</script>

<template>
  <div
    :class="itemClass"
    :data-disabled="disabled"
    @click="!disabled && $emit('select', value)"
  >
    <slot />
  </div>
</template>
