<script setup>
import { inject } from 'vue'
import { cn } from '@/lib/utils'
import { X } from 'lucide-vue-next'

const props = defineProps({
  class: String
})

const closeDialog = inject('dialog-close', () => {})
</script>

<template>
  <div :class="cn('p-6', props.class)">
    <!-- 关闭按钮 -->
    <button
      class="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
      @click="closeDialog"
    >
      <X class="h-4 w-4" />
      <span class="sr-only">关闭</span>
    </button>
    <slot />
  </div>
</template>
