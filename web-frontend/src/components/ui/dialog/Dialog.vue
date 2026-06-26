<script setup>
import { ref, watch, provide } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  open: Boolean,
  class: String
})

const emit = defineEmits(['update:open'])

const isOpen = ref(props.open)

watch(() => props.open, (val) => {
  isOpen.value = val
})

watch(isOpen, (val) => {
  emit('update:open', val)
})

provide('dialog-close', () => {
  isOpen.value = false
})

const onClose = () => {
  isOpen.value = false
}
</script>

<template>
  <Teleport to="body">
    <Transition name="dialog">
      <div v-if="isOpen" class="fixed inset-0 z-50">
        <!-- 背景遮罩 -->
        <div
          class="fixed inset-0 bg-black/80 transition-opacity"
          @click="onClose"
        />

        <!-- 居中容器 -->
        <div class="fixed inset-0 flex items-center justify-center p-4">
          <div
            :class="cn(
              'relative bg-background rounded-lg shadow-lg max-w-lg w-full max-h-[85vh] overflow-auto',
              props.class
            )"
            @click.stop
          >
            <slot />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.dialog-enter-active,
.dialog-leave-active {
  transition: opacity 0.2s ease;
}

.dialog-enter-from,
.dialog-leave-to {
  opacity: 0;
}
</style>
