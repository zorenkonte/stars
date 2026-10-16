// Stars Archive web reader — Nuxt 4, self-hosted (Nitro node-server preset).
// Reads the archive from Postgres (DATABASE_URL); see ../docker-compose.yml.
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  // Components are grouped in folders by feature; register them by file name only.
  components: [{ path: '~/components', pathPrefix: false }],
  app: {
    head: {
      title: 'Stars Archive',
      htmlAttrs: { lang: 'en' },
      meta: [
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'color-scheme', content: 'light dark' },
        { name: 'robots', content: 'noindex, nofollow' },
        { name: 'description', content: 'A browsable, append-only archive of starred GitHub repositories.' },
      ],
      link: [
        {
          rel: 'icon',
          href: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Ccircle cx='16' cy='16' r='16' fill='%23ffe566'/%3E%3Ctext x='16' y='23' font-size='20' text-anchor='middle' fill='%231a1530'%3E%E2%98%85%3C/text%3E%3C/svg%3E",
        },
      ],
    },
  },
  routeRules: {
    // The archive changes once a day; let browsers hold API answers briefly.
    '/api/**': { headers: { 'cache-control': 'private, max-age=30' } },
  },
  typescript: { strict: true },
})
