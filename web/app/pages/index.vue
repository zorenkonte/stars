<script setup lang="ts">
// Composition surface: URL-backed filters, server-side search pages, layout.
const { filters, set, reset, isDefault } = useCatalogQuery()
const { data: meta } = await useFetch('/api/meta')
const { firstItems, total, groups, facets, status, itemAt, ensureRange } = useRepoPages(filters)

const mainEl = shallowRef<HTMLElement | null>(null)
const { cols } = useColumns(mainEl, 4)

const queryKey = computed(() => JSON.stringify(filters.value))
const loading = computed(() => status.value === 'pending')

// Mobile: filters live in an off-canvas drawer.
const drawer = shallowRef(false)
watch(filters, () => (drawer.value = false))
watch(drawer, (open) => {
  if (import.meta.client) document.documentElement.style.overflow = open ? 'hidden' : ''
})
</script>

<template>
  <div class="shop">
    <CatalogHeader :meta="meta" />

    <div class="shop__body">
      <div class="shop__side" :class="{ 'shop__side--open': drawer }">
        <button type="button" class="shop__scrim" aria-label="Close filters" @click="drawer = false"></button>
        <div class="shop__panel">
          <FilterSidebar
            :q="filters.q"
            :status="filters.status"
            :lang="filters.lang"
            :list="filters.list"
            :facets="facets"
            :is-default="isDefault"
            @update:q="set('q', $event)"
            @update:status="set('status', $event)"
            @update:lang="set('lang', $event)"
            @update:list="set('list', $event)"
            @reset="reset()"
          />
        </div>
      </div>

      <main ref="mainEl" class="shop__main">
        <ResultsToolbar
          :sort="filters.sort"
          :group="filters.group"
          :total="total"
          :grand-total="meta?.total ?? total"
          :loading="loading"
          @update:sort="set('sort', $event)"
          @update:group="set('group', $event)"
          @open-filters="drawer = true"
        />

        <ClientOnly>
          <RepoGrid
            :total="total"
            :groups="groups"
            :cols="cols"
            :item-at="itemAt"
            :query-key="queryKey"
            @range="ensureRange"
          />
          <template #fallback>
            <!-- Server render: the first page as a plain grid so the page is never empty. -->
            <div class="shop__static">
              <RepoTile v-for="(repo, i) in firstItems" :key="repo.fullName" :repo="repo" :index="i" />
            </div>
          </template>
        </ClientOnly>
      </main>
    </div>

    <footer class="shop__foot">
      Served from a Cloudflare Worker · search runs on the server · archive is append-only
    </footer>
  </div>
</template>

<style scoped>
.shop { padding: 0 var(--pad) 80px; }
.shop__body {
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 32px;
  align-items: start;
}
.shop__side { position: sticky; top: 16px; }
.shop__panel { max-height: calc(100vh - 32px); overflow-y: auto; padding-right: 4px; scrollbar-width: thin; }
.shop__scrim { display: none; }
.shop__main { min-width: 0; }
.shop__static {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--gap);
}
.shop__foot {
  margin-top: 56px;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--ink-3);
  text-align: center;
}

@media (max-width: 999px) {
  .shop__body { grid-template-columns: minmax(0, 1fr); }
  .shop__side {
    position: fixed;
    inset: 0;
    z-index: 20;
    pointer-events: none;
  }
  .shop__scrim {
    display: block;
    position: absolute;
    inset: 0;
    border: 0;
    background: rgba(26, 21, 48, 0.45);
    opacity: 0;
    transition: opacity 0.32s var(--ease-snap);
  }
  .shop__panel {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: min(340px, 88vw);
    max-height: none;
    padding: 20px 20px 32px;
    background: var(--bg);
    border-right: 2px solid var(--ink);
    transform: translateX(-104%);
    transition: transform 0.55s var(--spring-snappy);
  }
  .shop__side--open { pointer-events: auto; }
  .shop__side--open .shop__scrim { opacity: 1; }
  .shop__side--open .shop__panel { transform: none; }
}
@media (prefers-reduced-motion: reduce) {
  .shop__panel, .shop__scrim { transition: none; }
}
</style>
