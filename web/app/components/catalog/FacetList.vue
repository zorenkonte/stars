<script setup lang="ts">
import type { Facet } from '~~/shared/types'

const props = withDefaults(
  defineProps<{
    title: string
    /** Label for the "no filter" row. */
    allLabel: string
    allCount: number
    options: Facet[]
    modelValue: string
    /** Extra fixed option rendered right after "all" (e.g. "Not in any list"). */
    extra?: Facet | null
    initialLimit?: number
  }>(),
  { extra: null, initialLimit: 10 },
)
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

const expanded = shallowRef(false)
const visible = computed(() => (expanded.value ? props.options : props.options.slice(0, props.initialLimit)))
const hidden = computed(() => Math.max(0, props.options.length - props.initialLimit))
// Keep the selected option visible even when collapsed.
const selectedHidden = computed(
  () => !expanded.value && props.modelValue !== '' && !visible.value.some((o) => o.value === props.modelValue),
)
const selected = computed(() => props.options.find((o) => o.value === props.modelValue) ?? null)

function pick(value: string) {
  emit('update:modelValue', value === props.modelValue ? '' : value)
}
</script>

<template>
  <section class="facet">
    <h3 class="facet__title">{{ title }}</h3>
    <ul class="facet__list" role="listbox" :aria-label="title">
      <li>
        <button type="button" class="facet__opt" :class="{ 'facet__opt--on': modelValue === '' }" role="option" :aria-selected="modelValue === ''" @click="pick('')">
          <span class="facet__label">{{ allLabel }}</span>
          <span class="facet__count">{{ allCount.toLocaleString('en-US') }}</span>
        </button>
      </li>
      <li v-if="extra">
        <button type="button" class="facet__opt" :class="{ 'facet__opt--on': modelValue === extra.value }" role="option" :aria-selected="modelValue === extra.value" @click="pick(extra.value)">
          <span class="facet__label">{{ extra.label }}</span>
          <span class="facet__count">{{ extra.count.toLocaleString('en-US') }}</span>
        </button>
      </li>
      <li v-if="selectedHidden && selected">
        <button type="button" class="facet__opt facet__opt--on" role="option" aria-selected="true" @click="pick(selected.value)">
          <span class="facet__label">{{ selected.label }}</span>
          <span class="facet__count">{{ selected.count.toLocaleString('en-US') }}</span>
        </button>
      </li>
      <li v-for="o in visible" :key="o.value">
        <button type="button" class="facet__opt" :class="{ 'facet__opt--on': modelValue === o.value, 'facet__opt--empty': o.count === 0 }" role="option" :aria-selected="modelValue === o.value" @click="pick(o.value)">
          <span class="facet__label">{{ o.label }}</span>
          <span class="facet__count">{{ o.count.toLocaleString('en-US') }}</span>
        </button>
      </li>
    </ul>
    <button v-if="hidden > 0" type="button" class="facet__more" @click="expanded = !expanded">
      {{ expanded ? 'Show fewer' : `Show all ${options.length}` }}
    </button>
  </section>
</template>

<style scoped>
.facet__title {
  margin: 0 0 8px;
  font-family: var(--font-display);
  font-size: 0.8rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink-3);
}
.facet__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.facet__opt {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 10px 7px 12px;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--ink-2);
  font-size: 0.9rem;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.32s var(--ease-snap), color 0.32s var(--ease-snap);
}
.facet__opt:hover { background: var(--tile); color: var(--tile-ink); }
.facet__opt--on { background: var(--ink); color: var(--bg); }
.facet__opt--on:hover { background: var(--ink); color: var(--bg); }
.facet__opt--empty { opacity: 0.45; }
.facet__label { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.facet__count { font-size: 0.75rem; font-weight: 700; opacity: 0.75; font-variant-numeric: tabular-nums; }
.facet__opt--on .facet__count { opacity: 0.85; }
.facet__more {
  margin-top: 6px;
  padding: 6px 12px;
  border: 1.5px solid var(--line);
  border-radius: 999px;
  background: transparent;
  color: var(--ink-2);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
}
.facet__more:hover { border-color: var(--ink); color: var(--ink); }
</style>
