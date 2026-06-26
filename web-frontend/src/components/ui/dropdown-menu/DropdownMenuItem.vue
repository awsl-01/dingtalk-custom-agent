<script setup>
import { inject, computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  disabled: Boolean,
  class: String,
  inset: Boolean
})

const closeDropdown = inject('closeDropdown', () => {})

const itemClass = computed(() => cn(
  'relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none transition-colors hover:bg-accent hover:text-accent-foreground focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
  props.inset && 'pl-8',
  props.class
))
</script>

<template>
  <div
    :class="itemClass"
    :data-disabled="disabled"
    @click="!disabled && closeDropdown()"
  >
    <slot />
  </div>
</template>
