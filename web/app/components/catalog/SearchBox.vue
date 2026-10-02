<script setup lang="ts">
const props = defineProps<{ modelValue: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

// Local echo so typing stays instant while the URL/server update is debounced.
const draft = shallowRef(props.modelValue)
watch(
  () => props.modelValue,
  (v) => {
    if (v !== draft.value) draft.value = v
  },
)

let timer: ReturnType<typeof setTimeout> | undefined
function onInput(e: Event) {
  draft.value = (e.target as HTMLInputElement).value
  clearTimeout(timer)
  timer = setTimeout(() => emit('update:modelValue', draft.value.trim()), 150)
}
function clear() {
  clearTimeout(timer)
  draft.value = ''
  emit('update:modelValue', '')
}
onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="search">
    <input
      class="pill-input search__input"
      type="search"
      :value="draft"
      placeholder="Search the archive…"
      aria-label="Search repositories"
      autocomplete="off"
      spellcheck="false"
      @input="onInput"
    >
    <button v-if="draft" class="search__clear" type="button" aria-label="Clear search" @click="clear">×</button>
  </div>
</template>

<style scoped>
.search { position: relative; }
.search__input { height: 52px; font-size: 1.05rem; padding-right: 44px; }
.search__clear {
  position: absolute;
  right: 10px;
  top: 50%;
  translate: 0 -50%;
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 50%;
  background: var(--ink);
  color: var(--bg);
  font-size: 1.1rem;
  font-weight: 800;
  cursor: pointer;
  display: grid;
  place-items: center;
}
</style>
