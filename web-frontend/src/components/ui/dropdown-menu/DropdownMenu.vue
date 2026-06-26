<script setup>
import { ref, provide, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  disabled: Boolean
})

const isOpen = ref(false)
const triggerRef = ref(null)

provide('dropdownOpen', isOpen)
provide('closeDropdown', () => {
  isOpen.value = false
})

const toggle = () => {
  if (!props.disabled) {
    isOpen.value = !isOpen.value
  }
}

const handleClickOutside = (event) => {
  if (triggerRef.value && !triggerRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<template>
  <div ref="triggerRef" class="relative inline-block">
    <div @click="toggle">
      <slot name="trigger" />
    </div>
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="fixed z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
        :style="{
          top: triggerRef ? triggerRef.getBoundingClientRect().bottom + 4 + 'px' : '0',
          left: triggerRef ? triggerRef.getBoundingClientRect().left + 'px' : '0'
        }"
      >
        <slot />
      </div>
    </Teleport>
  </div>
</template>
