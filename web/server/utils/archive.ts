import raw from '../../../stars.json'
import type { Repo, StarList } from '~~/shared/types'

/** Shape of the committed archive file (see repo README, "Entry shape"). */
interface RawRepo {
  full_name?: string
  html_url?: string
  description?: string | null
  language?: string | null
  stars?: number | string | null
  topics?: unknown
  lists?: unknown
  starred_at?: string | null
  first_seen?: string | null
  last_seen?: string | null
  gone_since?: string | null
  status?: string
}
interface RawArchive {
  repos?: Record<string, RawRepo>
  lists?: Record<string, { name?: string; description?: string | null; slug?: string }>
}

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
}

let cached: Archive | null = null

/** The archive is bundled at build time, so normalising it once per isolate is enough. */
export function getArchive(): Archive {
  if (cached) return cached
  cached = normalise(raw as RawArchive)
  return cached
}

function normalise(data: RawArchive): Archive {
  const lists = new Map<string, StarList>()
  for (const [slug, l] of Object.entries(data.lists ?? {})) {
    lists.set(slug, { slug, name: l?.name || slug, description: l?.description ?? '' })
  }
  const listName = (slug: string) => lists.get(slug)?.name ?? slug

  const repos: Repo[] = []
  const haystacks: string[] = []
  const langCounts = new Map<string, number>()
  let active = 0
  let gone = 0
  let lastSeen = ''

  for (const [key, r] of Object.entries(data.repos ?? {})) {
    const langKey = r.language || 'Other'
    const status = r.status === 'gone' ? 'gone' : 'active'
    if (status === 'gone') gone++
    else active++
    if (r.last_seen && r.last_seen > lastSeen) lastSeen = r.last_seen
    langCounts.set(langKey, (langCounts.get(langKey) ?? 0) + 1)

    const topics = Array.isArray(r.topics) ? r.topics.filter((t): t is string => typeof t === 'string') : []
    const slugs = Array.isArray(r.lists) ? r.lists.filter((s): s is string => typeof s === 'string' && s.length > 0) : []
    const listNames = slugs.map(listName)

    const repo: Repo = {
      fullName: r.full_name || key,
      htmlUrl: /^https?:\/\//i.test(r.html_url ?? '') ? (r.html_url as string) : '',
      description: r.description ?? '',
      language: r.language ?? null,
      langKey,
      stars: Number(r.stars) || 0,
      topics,
      lists: slugs,
      listNames,
      starredAt: r.starred_at ?? null,
      firstSeen: r.first_seen ?? null,
      goneSince: r.gone_since ?? null,
      status,
    }
    repos.push(repo)
    haystacks.push(
      [repo.fullName, repo.description, topics.join(' '), repo.language ?? '', listNames.join(' ')].join(' ').toLowerCase(),
    )
  }

  return { repos, haystacks, lists, langCounts, active, gone, lastSeen: lastSeen || null }
}
