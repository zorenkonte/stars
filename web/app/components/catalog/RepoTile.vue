<script setup lang="ts">
import type { Repo } from '~~/shared/types'

const props = defineProps<{ repo: Repo; index: number }>()

const gone = computed(() => props.repo.status === 'gone')
const tint = computed(() => `tile--tint-${props.index % 6}`)
const topics = computed(() => props.repo.topics.slice(0, 6).join(' · '))
</script>

<template>
  <article class="tile" :class="[tint, { 'tile--gone': gone }]">
    <span class="tile__lang">{{ repo.langKey }}</span>
    <span class="tile__stars"><span class="tile__stars-ico" aria-hidden="true">★</span> {{ fmtStars(repo.stars) }}</span>
    <span v-if="gone" class="tile__stamp">gone since {{ fmtDate(repo.goneSince) }}</span>

    <h3 class="tile__head">
      <a v-if="repo.htmlUrl" class="tile__name" :href="repo.htmlUrl" target="_blank" rel="noopener noreferrer">{{ repo.fullName }}</a>
      <span v-else class="tile__name">{{ repo.fullName }}</span>
    </h3>
    <p v-if="repo.description" class="tile__desc">{{ repo.description }}</p>

    <div class="tile__meta">
      <span v-if="topics" class="tile__topics">{{ topics }}</span>
      <span v-for="(name, i) in repo.listNames" :key="repo.lists[i]" class="tile__list" :title="`In list: ${name}`">
        <span class="tile__list-ico" aria-hidden="true">☰</span>{{ name }}
      </span>
      <span v-if="repo.starredAt" class="tile__date">starred {{ fmtDate(repo.starredAt) }}</span>
    </div>
  </article>
</template>

<style scoped>
.tile__head { margin: 0; font: inherit; }
</style>
