import type { Ref } from 'vue'
import type { Repo, ReposResponse } from '~~/shared/types'
// `ReposResponse` is used for the on-demand page fetches; page 0 is typed by useFetch's route inference.
import type { CatalogFilters } from './useCatalogQuery'

export const PAGE_SIZE = 60

/**
 * Server-side search with page-wise fetching for the virtual grid.
 *
 * Page 0 is fetched with useFetch so it renders on the server and re-fetches
 * whenever the filters change (facets, total and group spans come with it).
 * Further pages are fetched on demand from the client as the virtualizer
 * scrolls into ranges that are not loaded yet.
 */
export function useRepoPages(filters: Ref<CatalogFilters>) {
  const firstQuery = computed(() => ({ ...filters.value, offset: 0, limit: PAGE_SIZE }))

  // Response type is inferred from server/api/repos.get.ts (ReposResponse).
  // Stable key: one asyncData slot re-fetched when the query changes, instead of a new
  // slot (and a second request) per distinct query string.
  const { data: first, status, error } = useFetch('/api/repos', {
    key: 'repos-first-page',
    query: firstQuery,
    watch: [firstQuery],
    dedupe: 'cancel',
    // Reuse the server payload on hydration only; every later change must hit the API.
    getCachedData: (key, nuxtApp, ctx) => (ctx.cause === 'initial' ? nuxtApp.payload.data[key] : undefined),
  })

  // Pages other than the first, keyed by page index. Reset whenever page 0 changes.
  const extra = shallowRef(new Map<number, Repo[]>())
  const loading = new Set<number>()
  let generation = 0

  watch(first, () => {
    generation++
    loading.clear()
    extra.value = new Map()
  })

  const total = computed(() => first.value?.total ?? 0)
  const groups = computed(() => first.value?.groups ?? null)
  const facets = computed(() => first.value?.facets ?? null)
  const firstItems = computed(() => first.value?.items ?? [])

  function itemAt(index: number): Repo | undefined {
    if (index < PAGE_SIZE) return first.value?.items[index]
    const page = Math.floor(index / PAGE_SIZE)
    return extra.value.get(page)?.[index % PAGE_SIZE]
  }

  async function loadPage(page: number) {
    if (page === 0 || loading.has(page) || extra.value.has(page)) return
    loading.add(page)
    const gen = generation
    try {
      const res = await $fetch<ReposResponse>('/api/repos', {
        query: { ...filters.value, offset: page * PAGE_SIZE, limit: PAGE_SIZE },
      })
      if (gen !== generation) return // filters changed meanwhile; drop stale page
      const next = new Map(extra.value)
      next.set(page, res.items)
      extra.value = next
    } finally {
      loading.delete(page)
    }
  }

  /** Called by the grid with the item index range currently rendered (inclusive). */
  function ensureRange(startIndex: number, endIndex: number) {
    if (endIndex < startIndex) return
    const firstPage = Math.floor(Math.max(0, startIndex) / PAGE_SIZE)
    const lastPage = Math.floor(Math.min(endIndex, Math.max(0, total.value - 1)) / PAGE_SIZE)
    for (let p = firstPage; p <= lastPage + 1; p++) void loadPage(p) // +1 prefetches the next page
  }

  return { first, firstItems, total, groups, facets, status, error, itemAt, ensureRange }
}
