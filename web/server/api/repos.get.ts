import { getArchive } from '../utils/archive'
import { parseReposQuery, runReposQuery } from '../utils/query'

export default defineEventHandler(async (event) => {
  const query = parseReposQuery(getQuery(event))
  return runReposQuery(await getArchive(), query)
})
