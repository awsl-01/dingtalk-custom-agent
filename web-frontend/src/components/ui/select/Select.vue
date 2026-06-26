<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { cn } from '@/lib/utils'
import { ChevronDown, Check } from 'lucide-vue-next'

const props = defineProps({
  modelValue: [String, Number],
  placeholder: {
    type: String,
    default: '请选择'
  },
  disabled: Boolean,
  clearable: Boolean,
  class: String
})

const emit = defineEmits(['update:modelValue', 'change'])

const isOpen = ref(false)
const selectRef = ref(null)

const selectClass = computed(() => cn(
  'relative inline-flex items-center justify-between w-full h-10 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
  props.class
))

const toggleDropdown = () => {
  if (!props.disabled) {
    isOpen.value = !isOpen.value
  }
}

const selectOption = (value) => {
  emit('update:modelValue', value)
  emit('change', value)
  isOpen.value = false
}

const clearSelection = (e) => {
  e.stopPropagation()
  emit('update:modelValue', '')
  emit('change', '')
}

const handleClickOutside = (event) => {
  if (selectRef.value && !selectRef.value.contains(event.target)) {
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
  <div ref="selectRef" :class="selectClass" @click="toggleDropdown">
    <span :class="['truncate', !modelValue && 'text-muted-foreground']">
      <slot name="value" :value="modelValue">
        {{ modelValue || placeholder }}
      </slot>
    </span>

    <div class="flex items-center gap-1">
      <button
        v-if="clearable && modelValue"
        type="button"
        class="absolute right-8 top-1/2 -translate-y-1/2 rounded-sm opacity-70 hover:opacity-100"
        @click="clearSelection"
      >
        <span class="sr-only">清除</span>
        ×
      </button>
      <ChevronDown class="h-4 w-4 opacity-50 transition-transform" :class="{ 'rotate-180': isOpen }" />
    </div>

    <!-- 下拉选项 -->
    <Teleport to="body">
      <div
        v-if="isOpen"
        class="fixed z-50 min-w-[8rem] overflow-hidden rounded-md border bg-popover text-popover-foreground shadow-md animate-in fade-in-0 zoom-in-95"
        :style="{
          top: selectRef ? selectRef.getBoundingClientRect().bottom + 4 + 'px' : '0',
          left: selectRef ? selectRef.getBoundingClientRect().left + 'px' : '0',
          width: selectRef ? selectRef.getBoundingClientRect().width + 'px' : 'auto'
        }"
      >
        <div class="p-1">
          <slot />
        </div>
      </div>
    </Teleport>
  </div>
</template>
