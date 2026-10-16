import type { Repo, StarList } from '~~/shared/types'
import { getPool } from './db'

export interface Archive {
  repos: Repo[]
  /** Lower-cased search text per repo, parallel to `repos`. */
  haystacks: string[]
  lists: Map<string, StarList>
  /** Total repos per language key, used for group ordering (same as STARS.md). */
  langCounts: Map<string, number>
  active: number
  gone: number
  lastSeen: string | null
  /** When the Postgres mirror was last refreshed by the archiver. */
  syncedAt: string | null
}

interface RepoRow {
  full_name: string
  html_url: string
  description: string
  language: string | null
  stars: number
  topics: string[]
  lists: string[]
  starred_at: Date | null
  first_seen: Date | null
  last_seen: Date | null
  gone_since: Date | null
  status: 'active' | 'gone'
}
interface ListRow {
  slug: string
  name: string
  description: string
}

/**
 * The archive is ~1.5k rows, so the whole thing is loaded into memory and the
 * existing in-process query engine (query.ts) runs over it. The cache is
 * refreshed when sync_state.synced_at changes, checked at most once per
 * CHECK_INTERVAL_MS — that one tiny query is the only per-request DB cost.
 */
const CHECK_INTERVAL_MS = 15_000

let cached: Archive | null = null
let cachedSyncedAt: string | null = null
let lastCheck = 0
let inflight: Promise<Archive> | null = null

export async function getArchive(): Promise<Archive> {
  const now = Date.now()
  if (cached && now - lastCheck < CHECK_INTERVAL_MS) return cached
  if (inflight) return inflight
  inflight = refresh(now).finally(() => {
    inflight = null
  })
  return inflight
}

async function refresh(now: number): Promise<Archive> {
  const pool = getPool()
  const state = await pool.query<{ synced_at: Date | null }>('SELECT synced_at FROM sync_state WHERE id')
  const syncedAt = state.rows[0]?.synced_at?.toISOString() ?? null
  lastCheck = now
  if (cached && syncedAt === cachedSyncedAt) return cached

  const [repoRes, listRes] = await Promise.all([
    pool.query<RepoRow>(
      `SELECT full_name, html_url, description, language, stars, topics, lists,
              starred_at, first_seen, last_seen, gone_since, status
         FROM repos ORDER BY full_name`,
    ),
    pool.query<ListRow>('SELECT slug, name, description FROM lists'),
  ])
  cached = normalise(repoRes.rows, listRes.rows, syncedAt)
  cachedSyncedAt = syncedAt
  // An empty archive means the first sync hasn't happened yet; don't hold that for 15s.
  if (cached.repos.length === 0) lastCheck = 0
  return cached
}

const iso = (d: Date | null) => (d ? d.toISOString() : null)

function normalise(rows: RepoRow[], listRows: ListRow[], syncedAt: string | null): Archive {
  const lists = new Map<string, StarList>()
  for (const l of listRows) lists.set(l.slug, { slug: l.slug, name: l.name || l.slug, description: l.description ?? '' })
  const listName = (slug: string) => lists.get(slug)?.name ?? slug

  const repos: Repo[] = []
  const haystacks: string[] = []
  const langCounts = new Map<string, number>()
  let active = 0
  let gone = 0
  let lastSeen = ''

  for (const r of rows) {
    const langKey = r.language || 'Other'
    const status = r.status === 'gone' ? 'gone' : 'active'
    if (status === 'gone') gone++
    else active++
    const seen = iso(r.last_seen)
    if (seen && seen > lastSeen) lastSeen = seen
    langCounts.set(langKey, (langCounts.get(langKey) ?? 0) + 1)

    const topics = r.topics ?? []
    const slugs = r.lists ?? []
    const listNames = slugs.map(listName)
    const repo: Repo = {
      fullName: r.full_name,
      htmlUrl: /^https?:\/\//i.test(r.html_url ?? '') ? r.html_url : '',
      description: r.description ?? '',
      language: r.language,
      langKey,
      stars: Number(r.stars) || 0,
      topics,
      lists: slugs,
      listNames,
      starredAt: iso(r.starred_at),
      firstSeen: iso(r.first_seen),
      goneSince: iso(r.gone_since),
      status,
    }
    repos.push(repo)
    haystacks.push(
      [repo.fullName, repo.description, topics.join(' '), repo.language ?? '', listNames.join(' ')].join(' ').toLowerCase(),
    )
  }

  return { repos, haystacks, lists, langCounts, active, gone, lastSeen: lastSeen || null, syncedAt }
}
