<script setup lang="ts">
import { useWindowVirtualizer } from '@tanstack/vue-virtual'
import type { ComponentPublicInstance } from 'vue'
import type { GroupSpan, Repo } from '~~/shared/types'

type Row =
  | { kind: 'header'; key: string; label: string; count: number }
  | { kind: 'items'; key: string; start: number; end: number; header: string | null }

const props = defineProps<{
  total: number
  groups: GroupSpan[] | null
  cols: number
  itemAt: (index: number) => Repo | undefined
  /** Changes whenever the query changes; used to replay the intro pop on the first shelf. */
  queryKey: string
}>()
const emit = defineEmits<{ range: [start: number, end: number] }>()

const HEADER_H = 60
const TILE_H = 300

/** Rows are derived purely from total + group spans + columns; item data is resolved lazily. */
const rows = computed<Row[]>(() => {
  const out: Row[] = []
  const spans: GroupSpan[] = props.groups?.length ? props.groups : [{ label: '', start: 0, end: props.total }]
  for (const g of spans) {
    if (props.groups) out.push({ kind: 'header', key: `h:${g.label}`, label: g.label, count: g.end - g.start })
    for (let s = g.start; s < g.end; s += props.cols) {
      out.push({ kind: 'items', key: `r:${s}`, start: s, end: Math.min(s + props.cols, g.end), header: props.groups ? g.label : null })
    }
  }
  return out
})

const listEl = shallowRef<HTMLElement | null>(null)
const scrollMargin = shallowRef(0)
function measureMargin() {
  if (listEl.value) scrollMargin.value = listEl.value.getBoundingClientRect().top + window.scrollY
}
onMounted(() => {
  measureMargin()
  window.addEventListener('resize', measureMargin, { passive: true })
})
onBeforeUnmount(() => window.removeEventListener('resize', measureMargin))

const virtualizer = useWindowVirtualizer(
  computed(() => ({
    count: rows.value.length,
    estimateSize: (i: number) => (rows.value[i]?.kind === 'header' ? HEADER_H : TILE_H),
    overscan: 3,
    gap: 20,
    scrollMargin: scrollMargin.value,
    getItemKey: (i: number) => rows.value[i]?.key ?? i,
  })),
)

const virtualRows = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

// Tell the data layer which item indexes are on screen so it can fetch pages.
watch(
  virtualRows,
  (vs) => {
    let lo = Number.POSITIVE_INFINITY
    let hi = -1
    for (const v of vs) {
      const r = rows.value[v.index]
      if (r?.kind === 'items') {
        lo = Math.min(lo, r.start)
        hi = Math.max(hi, r.end - 1)
      }
    }
    if (hi >= 0) emit('range', lo, hi)
  },
  { immediate: true },
)

// Pinned shelf label: the group the first visible row belongs to.
const pinned = computed(() => {
  const offset = virtualizer.value.scrollOffset ?? 0
  const first = virtualRows.value.find((v) => v.end > offset)
  const r = first ? rows.value[first.index] : undefined
  if (!r || r.kind !== 'items' || !r.header) return null
  const g = props.groups?.find((g) => g.label === r.header)
  return g ? { label: g.label, count: g.end - g.start } : null
})

// Rows are re-keyed per query so the first shelf pops again after a search/filter.
const introRows = computed(() => new Set(rows.value.slice(0, 4).map((r) => r.key)))

function measure(el: Element | ComponentPublicInstance | null) {
  if (el instanceof Element) virtualizer.value.measureElement(el)
}
</script>

<template>
  <div ref="listEl" class="grid" :style="{ height: `${totalSize}px` }">
    <Transition name="pin">
      <div v-if="pinned" class="grid__pinned" aria-hidden="true">
        <span class="grid__pinned-label">{{ pinned.label }}</span>
        <span class="chip-count">{{ pinned.count.toLocaleString('en-US') }}</span>
      </div>
    </Transition>

    <template v-for="v in virtualRows" :key="`${queryKey}:${v.key}`">
      <div
        v-if="rows[v.index]?.kind === 'header'"
        :ref="measure"
        :data-index="v.index"
        class="grid__row grid__header"
        :style="{ transform: `translateY(${v.start - scrollMargin}px)` }"
      >
        <span class="grid__header-label">{{ (rows[v.index] as Extract<Row, { kind: 'header' }>).label }}</span>
        <span class="chip-count">{{ (rows[v.index] as Extract<Row, { kind: 'header' }>).count.toLocaleString('en-US') }}</span>
      </div>
      <div
        v-else
        :ref="measure"
        :data-index="v.index"
        class="grid__row grid__shelf"
        :class="{ pop: introRows.has(v.key as string), [`pop--${Math.min(3, v.index)}`]: introRows.has(v.key as string) }"
        :style="{ transform: `translateY(${v.start - scrollMargin}px)`, '--cols': cols }"
      >
        <template v-for="i in (rows[v.index] as Extract<Row, { kind: 'items' }>).end - (rows[v.index] as Extract<Row, { kind: 'items' }>).start" :key="i">
          <RepoTile
            v-if="itemAt((rows[v.index] as Extract<Row, { kind: 'items' }>).start + i - 1)"
            :repo="itemAt((rows[v.index] as Extract<Row, { kind: 'items' }>).start + i - 1)!"
            :index="(rows[v.index] as Extract<Row, { kind: 'items' }>).start + i - 1"
          />
          <div v-else class="tile tile--skeleton" aria-hidden="true"></div>
        </template>
      </div>
    </template>

    <p v-if="total === 0" class="grid__empty">Nothing on the shelves for that. Try a different search or clear the filters.</p>
  </div>
</template>

<style scoped>
.grid { position: relative; width: 100%; }
.grid__row { position: absolute; top: 0; left: 0; width: 100%; }
.grid__shelf {
  display: grid;
  grid-template-columns: repeat(var(--cols, 4), minmax(0, 1fr));
  gap: var(--gap);
  align-items: stretch;
}
.grid__header,
.grid__pinned {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-display);
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
}
.grid__header { height: 60px; padding-top: 12px; }
.grid__header-label,
.grid__pinned-label { box-shadow: inset 0 -0.42em var(--lemon); padding: 0 0.12em; }
.grid__pinned {
  position: sticky;
  top: 0;
  z-index: 3;
  margin: 0 calc(-1 * var(--pad));
  padding: 10px var(--pad);
  background: var(--bg);
  border-bottom: 2px solid var(--ink);
  font-size: 1.15rem;
}
.pin-enter-active,
.pin-leave-active { transition: opacity 0.25s var(--ease-snap), transform 0.4s var(--spring-snappy); }
.pin-enter-from,
.pin-leave-to { opacity: 0; transform: translateY(-8px); }
.tile--skeleton {
  min-height: 260px;
  background: linear-gradient(100deg, var(--tile) 40%, color-mix(in srgb, var(--tile) 85%, var(--ink)) 50%, var(--tile) 60%) 0 0 / 250% 100%;
  animation: shimmer 1.2s linear infinite;
  border-color: transparent;
}
@keyframes shimmer { to { background-position: -150% 0; } }
.grid__empty {
  padding: 48px 0;
  text-align: center;
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--ink-2);
}
</style>
