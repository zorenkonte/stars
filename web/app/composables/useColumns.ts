import type { Ref } from 'vue'

/** Tile columns for a given container width. Tiles want roughly 260–340px each. */
export function columnsFor(width: number): number {
  if (width < 520) return 1
  if (width < 800) return 2
  if (width < 1080) return 3
  if (width < 1400) return 4
  return 5
}

/** Tracks a container's width with ResizeObserver and derives the column count. */
export function useColumns(el: Ref<HTMLElement | null>, initial = 4) {
  const width = shallowRef(0)
  const cols = computed(() => (width.value ? columnsFor(width.value) : initial))

  let ro: ResizeObserver | null = null
  onMounted(() => {
    if (!el.value) return
    width.value = el.value.clientWidth
    ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width
      if (w) width.value = w
    })
    ro.observe(el.value)
  })
  onBeforeUnmount(() => ro?.disconnect())

  return { cols, width }
}
