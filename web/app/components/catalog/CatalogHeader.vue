<script setup lang="ts">
import type { MetaResponse } from '~~/shared/types'

defineProps<{ meta: MetaResponse | null | undefined }>()
</script>

<template>
  <header class="masthead pop">
    <h1 class="masthead__title">Stars Archive</h1>
    <div v-if="meta" class="masthead__stats" aria-live="polite">
      <span><strong>{{ meta.total.toLocaleString('en-US') }}</strong> total</span>
      <span><strong>{{ meta.active.toLocaleString('en-US') }}</strong> active</span>
      <span><strong>{{ meta.gone.toLocaleString('en-US') }}</strong> gone</span>
      <span v-if="meta.lastSeen">updated {{ fmtDate(meta.lastSeen) }}</span>
    </div>
  </header>
</template>

<style scoped>
.masthead {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px 32px;
  padding: clamp(24px, 4vw, 44px) 0 18px;
}
.masthead__title {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.18em;
  font-family: var(--font-display);
  font-size: clamp(2.6rem, 6.5vw, 5.5rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 0.9;
}
.masthead__title::before {
  content: "\2605";
  display: inline-grid;
  place-items: center;
  width: 1.2em;
  height: 1.2em;
  border-radius: 50%;
  background: var(--lemon);
  color: var(--tag-ink);
  font-size: 0.5em;
  line-height: 1;
  transform: rotate(-10deg);
  flex: none;
}
.masthead__stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--ink-2);
  font-variant-numeric: tabular-nums;
  padding-bottom: 0.4em;
}
.masthead__stats > span {
  background: var(--tile);
  color: var(--tile-ink-2);
  border: 1.5px solid var(--line);
  border-radius: 999px;
  padding: 6px 12px;
}
.masthead__stats strong { color: var(--tile-ink); font-weight: 800; }
</style>
