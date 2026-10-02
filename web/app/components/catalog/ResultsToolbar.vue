<script setup lang="ts">
import type { GroupKey, SortKey } from '~~/shared/types'

defineProps<{
  sort: SortKey
  group: GroupKey
  total: number
  grandTotal: number
  loading: boolean
}>()
const emit = defineEmits<{
  'update:sort': [value: SortKey]
  'update:group': [value: GroupKey]
  'open-filters': []
}>()
</script>

<template>
  <div class="toolbar">
    <button type="button" class="toolbar__filters" @click="emit('open-filters')">Filters</button>
    <p class="toolbar__count" aria-live="polite">
      <span v-if="loading" class="toolbar__dot" aria-hidden="true"></span>
      showing <strong>{{ total.toLocaleString('en-US') }}</strong> of {{ grandTotal.toLocaleString('en-US') }}
    </p>
    <label class="toolbar__field">
      Sort
      <select class="pill-select" :value="sort" aria-label="Sort repositories" @change="emit('update:sort', ($event.target as HTMLSelectElement).value as SortKey)">
        <option value="starred">Recently starred</option>
        <option value="stars">Most stars</option>
        <option value="added">Recently added</option>
        <option value="name">Name (A–Z)</option>
      </select>
    </label>
    <label class="toolbar__field">
      Group
      <select class="pill-select" :value="group" aria-label="Group repositories" @change="emit('update:group', ($event.target as HTMLSelectElement).value as GroupKey)">
        <option value="">None</option>
        <option value="language">Language</option>
        <option value="status">Status</option>
      </select>
    </label>
  </div>
</template>

<style scoped>
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px 14px;
  padding-bottom: 14px;
}
.toolbar__count {
  margin: 0 auto 0 0;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--ink-2);
  font-variant-numeric: tabular-nums;
}
.toolbar__count strong { color: var(--ink); font-weight: 800; }
.toolbar__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--lemon);
  animation: pulse 0.9s var(--spring-smooth) infinite alternate;
}
@keyframes pulse { from { opacity: 0.3; } to { opacity: 1; } }
.toolbar__field {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--ink-3);
}
.toolbar__filters {
  display: none;
  height: 46px;
  padding: 0 18px;
  border: 1.5px solid var(--ink);
  border-radius: 999px;
  background: var(--ink);
  color: var(--bg);
  font-weight: 800;
  cursor: pointer;
}
@media (max-width: 999px) {
  .toolbar__filters { display: inline-flex; align-items: center; }
}
@media (max-width: 600px) {
  .toolbar__count { order: 9; flex-basis: 100%; }
}
</style>
