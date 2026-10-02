import { GROUP_KEYS, SORT_KEYS, STATUS_FILTERS, type GroupKey, type SortKey, type StatusFilter } from '~~/shared/types'

export interface CatalogFilters {
  q: string
  lang: string
  list: string
  status: StatusFilter
  sort: SortKey
  group: GroupKey
}

const DEFAULTS: CatalogFilters = { q: '', lang: '', list: '', status: 'all', sort: 'starred', group: '' }

function one(v: unknown): string {
  if (Array.isArray(v)) return typeof v[0] === 'string' ? v[0] : ''
  return typeof v === 'string' ? v : ''
}
function pick<T extends string>(v: unknown, allowed: readonly T[], fallback: T): T {
  const s = one(v)
  return (allowed as readonly string[]).includes(s) ? (s as T) : fallback
}

/**
 * Filter state lives in the URL query so views are shareable and survive reloads.
 * Reading is a computed over the route; writing replaces the query (no history spam).
 */
export function useCatalogQuery() {
  const route = useRoute()
  const router = useRouter()

  const filters = computed<CatalogFilters>(() => ({
    q: one(route.query.q),
    lang: one(route.query.lang),
    list: one(route.query.list),
    status: pick<StatusFilter>(route.query.status, STATUS_FILTERS, DEFAULTS.status),
    sort: pick<SortKey>(route.query.sort, SORT_KEYS, DEFAULTS.sort),
    group: pick<GroupKey>(route.query.group, GROUP_KEYS, DEFAULTS.group),
  }))

  function set<K extends keyof CatalogFilters>(key: K, value: CatalogFilters[K]) {
    const next: Record<string, string> = {}
    const merged = { ...filters.value, [key]: value }
    for (const k of Object.keys(DEFAULTS) as (keyof CatalogFilters)[]) {
      if (merged[k] !== DEFAULTS[k] && merged[k] !== '') next[k] = merged[k]
    }
    router.replace({ query: next })
  }

  function reset() {
    router.replace({ query: {} })
  }

  const isDefault = computed(() =>
    (Object.keys(DEFAULTS) as (keyof CatalogFilters)[]).every((k) => filters.value[k] === DEFAULTS[k]),
  )

  return { filters, set, reset, isDefault }
}
