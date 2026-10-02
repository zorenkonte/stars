export function fmtStars(n: number): string {
  return (Number(n) || 0).toLocaleString('en-US')
}

export function fmtDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  // Fixed locale and time zone so the Worker (UTC) and the browser render the same string.
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', timeZone: 'UTC' })
}
