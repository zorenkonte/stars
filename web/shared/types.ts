export type Status = 'active' | 'gone'
export type StatusFilter = Status | 'all'
export type SortKey = 'stars' | 'starred' | 'added' | 'name'
export type GroupKey = '' | 'language' | 'status'

export const SORT_KEYS: readonly SortKey[] = ['stars', 'starred', 'added', 'name']
export const GROUP_KEYS: readonly GroupKey[] = ['', 'language', 'status']
export const STATUS_FILTERS: readonly StatusFilter[] = ['active', 'gone', 'all']

/** Sentinel value for the list filter meaning "repos that belong to no list". */
export const NO_LIST = '__none__'

export interface Repo {
  fullName: string
  htmlUrl: string
  description: string
  language: string | null
  /** Language used for filtering/grouping; "Other" when GitHub reports none. */
  langKey: string
  stars: number
  topics: string[]
  /** Star-list slugs this repo belongs to. */
  lists: string[]
  /** Display names for `lists`, same order. */
  listNames: string[]
  starredAt: string | null
  firstSeen: string | null
  goneSince: string | null
  status: Status
}

export interface StarList {
  slug: string
  name: string
  description: string
}

export interface Facet {
  value: string
  label: string
  count: number
}

export interface GroupSpan {
  label: string
  start: number
  end: number
}

export interface ReposQuery {
  q: string
  lang: string
  list: string
  status: StatusFilter
  sort: SortKey
  group: GroupKey
  offset: number
  limit: number
}

export interface Facets {
  languages: Facet[]
  lists: Facet[]
  notInAnyList: number
  status: { active: number; gone: number; all: number }
}

export interface ReposResponse {
  total: number
  offset: number
  limit: number
  items: Repo[]
  /** Contiguous spans over the whole filtered+sorted result, or null when ungrouped. */
  groups: GroupSpan[] | null
  facets: Facets
}

export interface MetaResponse {
  total: number
  active: number
  gone: number
  lastSeen: string | null
  languages: Facet[]
  lists: Facet[]
  notInAnyList: number
}
