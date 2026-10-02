<script setup lang="ts">
import { NO_LIST, type Facets, type StatusFilter } from '~~/shared/types'

const props = defineProps<{
  q: string
  status: StatusFilter
  lang: string
  list: string
  facets: Facets | null
  isDefault: boolean
}>()
const emit = defineEmits<{
  'update:q': [value: string]
  'update:status': [value: StatusFilter]
  'update:lang': [value: string]
  'update:list': [value: string]
  reset: []
}>()

const languages = computed(() => props.facets?.languages ?? [])
const lists = computed(() => props.facets?.lists ?? [])
const langAll = computed(() => languages.value.reduce((n, f) => n + f.count, 0))
const listAll = computed(() => props.facets?.status.all ?? 0)
const notInAnyList = computed(() =>
  props.facets ? { value: NO_LIST, label: 'Not in any list', count: props.facets.notInAnyList } : null,
)
</script>

<template>
  <aside class="filters" aria-label="Filters">
    <div class="filters__head">
      <h2 class="filters__title">Filters</h2>
      <button v-if="!isDefault" type="button" class="filters__reset" @click="emit('reset')">Reset</button>
    </div>

    <SearchBox :model-value="q" @update:model-value="emit('update:q', $event)" />

    <StatusToggle :model-value="status" :counts="facets?.status ?? null" @update:model-value="emit('update:status', $event)" />

    <FacetList
      title="Language"
      all-label="All languages"
      :all-count="langAll"
      :options="languages"
      :model-value="lang"
      @update:model-value="emit('update:lang', $event)"
    />

    <FacetList
      v-if="lists.length"
      title="Star lists"
      all-label="All lists"
      :all-count="listAll"
      :options="lists"
      :extra="notInAnyList"
      :model-value="list"
      @update:model-value="emit('update:list', $event)"
    />
  </aside>
</template>

<style scoped>
.filters {
  display: flex;
  flex-direction: column;
  gap: 22px;
}
.filters__head { display: flex; align-items: baseline; justify-content: space-between; }
.filters__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.4rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}
.filters__reset {
  padding: 4px 12px;
  border: 1.5px solid var(--ink);
  border-radius: 999px;
  background: transparent;
  color: var(--ink);
  font-size: 0.78rem;
  font-weight: 800;
  cursor: pointer;
}
.filters__reset:hover { background: var(--ink); color: var(--bg); }
</style>
