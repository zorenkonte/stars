import { getArchive } from '../utils/archive'
import { parseReposQuery, runReposQuery } from '../utils/query'

export default defineEventHandler((event) => {
  const query = parseReposQuery(getQuery(event))
  return runReposQuery(getArchive(), query)
})
