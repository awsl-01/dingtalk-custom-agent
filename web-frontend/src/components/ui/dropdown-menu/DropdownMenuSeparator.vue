<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  class: String
})
</script>

<template>
  <div :class="cn('-mx-1 my-1 h-px bg-muted', props.class)" />
</template>
