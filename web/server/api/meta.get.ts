import { getArchive } from '../utils/archive'
import type { Facet, MetaResponse } from '~~/shared/types'

export default defineEventHandler((): MetaResponse => {
  const archive = getArchive()
  const listCounts = new Map<string, number>()
  let notInAnyList = 0
  for (const r of archive.repos) {
    if (r.lists.length === 0) notInAnyList++
    for (const s of r.lists) listCounts.set(s, (listCounts.get(s) ?? 0) + 1)
  }
  const languages: Facet[] = [...archive.langCounts.entries()]
    .map(([value, count]) => ({ value, label: value, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
  const lists: Facet[] = [...archive.lists.values()]
    .map((l) => ({ value: l.slug, label: l.name, count: listCounts.get(l.slug) ?? 0 }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label))
  return {
    total: archive.repos.length,
    active: archive.active,
    gone: archive.gone,
    lastSeen: archive.lastSeen,
    languages,
    lists,
    notInAnyList,
  }
})
