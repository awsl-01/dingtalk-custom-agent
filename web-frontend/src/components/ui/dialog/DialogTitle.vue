<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  class: String
})
</script>

<template>
  <h2
    :class="cn(
      'text-lg font-semibold leading-none tracking-tight',
      props.class
    )"
  >
    <slot />
  </h2>
</template>
