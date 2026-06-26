<script setup>
import { computed } from 'vue'
import { cn } from '@/lib/utils'
import { ChevronLeft, ChevronRight, MoreHorizontal } from 'lucide-vue-next'
import Button from '@/components/ui/button/Button.vue'

const props = defineProps({
  currentPage: {
    type: Number,
    default: 1
  },
  total: {
    type: Number,
    default: 0
  },
  pageSize: {
    type: Number,
    default: 10
  },
  class: String
})

const emit = defineEmits(['update:currentPage', 'change'])

const totalPages = computed(() => Math.ceil(props.total / props.pageSize))

const pages = computed(() => {
  const result = []
  const current = props.currentPage
  const total = totalPages.value

  if (total <= 7) {
    for (let i = 1; i <= total; i++) {
      result.push(i)
    }
  } else {
    if (current <= 3) {
      for (let i = 1; i <= 5; i++) {
        result.push(i)
      }
      result.push('...')
      result.push(total)
    } else if (current >= total - 2) {
      result.push(1)
      result.push('...')
      for (let i = total - 4; i <= total; i++) {
        result.push(i)
      }
    } else {
      result.push(1)
      result.push('...')
      for (let i = current - 1; i <= current + 1; i++) {
        result.push(i)
      }
      result.push('...')
      result.push(total)
    }
  }

  return result
})

const goToPage = (page) => {
  if (page === '...' || page < 1 || page > totalPages.value || page === props.currentPage) {
    return
  }
  emit('update:currentPage', page)
  emit('change', page)
}

const prevPage = () => {
  if (props.currentPage > 1) {
    goToPage(props.currentPage - 1)
  }
}

const nextPage = () => {
  if (props.currentPage < totalPages.value) {
    goToPage(props.currentPage + 1)
  }
}
</script>

<template>
  <nav :class="cn('flex items-center justify-center space-x-1', props.class)">
    <Button
      variant="outline"
      size="icon"
      :disabled="currentPage === 1"
      @click="prevPage"
    >
      <ChevronLeft class="h-4 w-4" />
    </Button>

    <template v-for="(page, index) in pages" :key="index">
      <Button
        v-if="page === '...'"
        variant="outline"
        size="icon"
        disabled
      >
        <MoreHorizontal class="h-4 w-4" />
      </Button>
      <Button
        v-else
        :variant="page === currentPage ? 'default' : 'outline'"
        size="icon"
        @click="goToPage(page)"
      >
        {{ page }}
      </Button>
    </template>

    <Button
      variant="outline"
      size="icon"
      :disabled="currentPage === totalPages"
      @click="nextPage"
    >
      <ChevronRight class="h-4 w-4" />
    </Button>
  </nav>
</template>
