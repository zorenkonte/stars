// Stars Archive web reader — Nuxt 4 on Cloudflare Workers.
// The archive (../stars.json) is bundled into the server at build time; the
// deploy workflow rebuilds whenever the daily archive commit lands.
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: false },
  modules: ['nitro-cloudflare-dev'],
  nitro: {
    preset: 'cloudflare_module',
    cloudflare: {
      // wrangler.jsonc is hand-maintained; don't let Nitro generate one.
      deployConfig: false,
      nodeCompat: true,
    },
  },
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
    // Search results are deterministic for a given build; let the edge hold them briefly.
    '/api/**': { headers: { 'cache-control': 'public, max-age=60, stale-while-revalidate=300' } },
  },
  typescript: { strict: true },
})
