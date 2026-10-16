import { Pool } from 'pg'

let pool: Pool | null = null

/** One shared connection pool per process, configured by DATABASE_URL. */
export function getPool(): Pool {
  if (pool) return pool
  const connectionString = process.env.DATABASE_URL
  if (!connectionString) throw new Error('DATABASE_URL is not set')
  pool = new Pool({ connectionString, max: 4, idleTimeoutMillis: 30_000 })
  return pool
}
