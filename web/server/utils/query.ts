import type { QueryObject } from 'ufo'
import type { Archive } from './archive'
import {
  GROUP_KEYS,
  NO_LIST,
  SORT_KEYS,
  STATUS_FILTERS,
  type Facet,
  type Facets,
  type GroupKey,
  type GroupSpan,
  type Repo,
  type ReposQuery,
  type ReposResponse,
  type SortKey,
  type StatusFilter,
} from '~~/shared/types'

export const DEFAULT_LIMIT = 60
export const MAX_LIMIT = 200

function pick<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === 'string' && (allowed as readonly string[]).includes(value) ? (value as T) : fallback
}
function str(value: unknown): string {
  return typeof value === 'string' ? value : ''
}
function int(value: unknown, fallback: number, min: number, max: number): number {
  const n = typeof value === 'string' ? Number.parseInt(value, 10) : Number.NaN
  if (!Number.isFinite(n)) return fallback
  return Math.min(max, Math.max(min, n))
}

export function parseReposQuery(query: QueryObject): ReposQuery {
  return {
    q: str(query.q).trim().toLowerCase(),
    lang: str(query.lang),
    list: str(query.list),
    status: pick<StatusFilter>(query.status, STATUS_FILTERS, 'all'),
    sort: pick<SortKey>(query.sort, SORT_KEYS, 'starred'),
    group: pick<GroupKey>(query.group, GROUP_KEYS, ''),
    offset: int(query.offset, 0, 0, Number.MAX_SAFE_INTEGER),
    limit: int(query.limit, DEFAULT_LIMIT, 1, MAX_LIMIT),
  }
}

// Descending date compare with nulls sorted last.
function cmpDateDesc(a: string | null, b: string | null): number {
  if (!a && !b) return 0
  if (!a) return 1
  if (!b) return -1
  return a < b ? 1 : a > b ? -1 : 0
}

const SORTERS: Record<SortKey, (a: Repo, b: Repo) => number> = {
  stars: (a, b) => b.stars - a.stars || a.fullName.localeCompare(b.fullName),
  starred: (a, b) => cmpDateDesc(a.starredAt, b.starredAt) || a.fullName.localeCompare(b.fullName),
  added: (a, b) => cmpDateDesc(a.firstSeen, b.firstSeen) || a.fullName.localeCompare(b.fullName),
  name: (a, b) => a.fullName.toLowerCase().localeCompare(b.fullName.toLowerCase()),
}

type Dim = 'q' | 'status' | 'lang' | 'list'

/** Index-based filter so we can skip one dimension when computing its own facet counts. */
function matches(archive: Archive, i: number, q: ReposQuery, skip?: Dim): boolean {
  const r = archive.repos[i]!
  if (skip !== 'status' && q.status !== 'all' && r.status !== q.status) return false
  if (skip !== 'lang' && q.lang && r.langKey !== q.lang) return false
  if (skip !== 'list' && q.list) {
    if (q.list === NO_LIST) {
      if (r.lists.length) return false
    } else if (!r.lists.includes(q.list)) {
      return false
    }
  }
  if (skip !== 'q' && q.q && !archive.haystacks[i]!.includes(q.q)) return false
  return true
}

function groupRows(archive: Archive, rows: Repo[], mode: GroupKey): GroupSpan[] | null {
  if (!mode) return null
  const keyOf = mode === 'status' ? (r: Repo) => r.status : (r: Repo) => r.langKey
  const buckets = new Map<string, Repo[]>()
  for (const r of rows) {
    const k = keyOf(r)
    let b = buckets.get(k)
    if (!b) buckets.set(k, (b = []))
    b.push(r)
  }
  const keys = [...buckets.keys()]
  if (mode === 'status') {
    keys.sort((a, b) => (a === 'active' ? 0 : 1) - (b === 'active' ? 0 : 1))
  } else {
    // Same order as STARS.md: most repos first, then name.
    keys.sort((a, b) => (archive.langCounts.get(b) ?? 0) - (archive.langCounts.get(a) ?? 0) || a.localeCompare(b))
  }
  const groups: GroupSpan[] = []
  let pos = 0
  for (const k of keys) {
    const b = buckets.get(k)!
    for (let j = 0; j < b.length; j++) rows[pos + j] = b[j]!
    groups.push({ label: mode === 'status' ? (k === 'gone' ? 'Gone' : 'Active') : k, start: pos, end: pos + b.length })
    pos += b.length
  }
  return groups
}

function facets(archive: Archive, q: ReposQuery): Facets {
  const langCounts = new Map<string, number>()
  const listCounts = new Map<string, number>()
  let notInAnyList = 0
  const status = { active: 0, gone: 0, all: 0 }
  const n = archive.repos.length
  for (let i = 0; i < n; i++) {
    const r = archive.repos[i]!
    if (matches(archive, i, q, 'lang')) langCounts.set(r.langKey, (langCounts.get(r.langKey) ?? 0) + 1)
    if (matches(archive, i, q, 'list')) {
      if (r.lists.length === 0) notInAnyList++
      for (const s of r.lists) listCounts.set(s, (listCounts.get(s) ?? 0) + 1)
    }
    if (matches(archive, i, q, 'status')) {
      status.all++
      if (r.status === 'gone') status.gone++
      else status.active++
    }
  }
  const languages: Facet[] = [...langCounts.entries()]
    .map(([value, count]) => ({ value, label: value, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
  const lists: Facet[] = [...archive.lists.values()]
    .map((l) => ({ value: l.slug, label: l.name, count: listCounts.get(l.slug) ?? 0 }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
  return { languages, lists, notInAnyList, status }
}

export function runReposQuery(archive: Archive, q: ReposQuery): ReposResponse {
  const out: Repo[] = []
  for (let i = 0; i < archive.repos.length; i++) {
    if (matches(archive, i, q)) out.push(archive.repos[i]!)
  }
  out.sort(SORTERS[q.sort])
  const groups = groupRows(archive, out, q.group)
  return {
    total: out.length,
    offset: q.offset,
    limit: q.limit,
    items: out.slice(q.offset, q.offset + q.limit),
    groups,
    facets: facets(archive, q),
  }
}
