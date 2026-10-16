import { getArchive } from '../utils/archive'

/** Liveness for docker healthchecks: DB reachable and the archive loaded. */
export default defineEventHandler(async () => {
  const archive = await getArchive()
  return { ok: true, repos: archive.repos.length, syncedAt: archive.syncedAt }
})
