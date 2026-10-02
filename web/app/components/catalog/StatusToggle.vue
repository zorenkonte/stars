<script setup lang="ts">
import type { StatusFilter } from '~~/shared/types'

defineProps<{
  modelValue: StatusFilter
  counts: { active: number; gone: number; all: number } | null
}>()
const emit = defineEmits<{ 'update:modelValue': [value: StatusFilter] }>()

const options: { value: StatusFilter; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'gone', label: 'Gone' },
  { value: 'all', label: 'All' },
]
</script>

<template>
  <fieldset class="seg" role="radiogroup" aria-label="Status filter">
    <legend class="visually-hidden">Status</legend>
    <label v-for="o in options" :key="o.value" class="seg__opt" :class="{ 'seg__opt--on': o.value === modelValue }">
      <input
        class="visually-hidden"
        type="radio"
        name="status"
        :value="o.value"
        :checked="o.value === modelValue"
        @change="emit('update:modelValue', o.value)"
      >
      <span>{{ o.label }}</span>
      <small v-if="counts">{{ counts[o.value].toLocaleString('en-US') }}</small>
    </label>
  </fieldset>
</template>

<style scoped>
.seg {
  display: flex;
  gap: 2px;
  background: var(--tile);
  border: 1.5px solid var(--ink);
  border-radius: 999px;
  padding: 4px;
  margin: 0;
  min-width: 0;
}
.seg__opt {
  flex: 1 1 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 38px;
  padding: 0 10px;
  border-radius: 999px;
  cursor: pointer;
  user-select: none;
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--tile-ink-2);
  transition: background-color 0.4s var(--spring-smooth), color 0.4s var(--spring-smooth);
}
.seg__opt small { font-size: 0.72rem; font-weight: 700; opacity: 0.7; font-variant-numeric: tabular-nums; }
.seg__opt:hover { color: var(--tile-ink); }
.seg__opt--on { background: var(--tile-ink); color: var(--tile); }
.seg__opt:has(:focus-visible) { box-shadow: 0 0 0 3px var(--lemon); }
@media (prefers-color-scheme: dark) {
  .seg { border-color: var(--tile); }
}
.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
