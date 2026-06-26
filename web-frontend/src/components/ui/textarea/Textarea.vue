<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'

const props = defineProps({
  modelValue: String,
  placeholder: String,
  disabled: Boolean,
  readonly: Boolean,
  rows: {
    type: Number,
    default: 3
  },
  class: String
})

const emit = defineEmits(['update:modelValue'])

const textareaClass = computed(() => cn(
  'flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
  props.class
))

const onInput = (event) => {
  emit('update:modelValue', event.target.value)
}
</script>

<template>
  <textarea
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    :rows="rows"
    :class="textareaClass"
    @input="onInput"
  />
</template>
