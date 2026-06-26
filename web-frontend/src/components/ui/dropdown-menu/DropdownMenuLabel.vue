<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  class: String,
  inset: Boolean
})
</script>

<template>
  <div :class="cn(
    'px-2 py-1.5 text-sm font-semibold',
    props.inset && 'pl-8',
    props.class
  )">
    <slot />
  </div>
</template>
