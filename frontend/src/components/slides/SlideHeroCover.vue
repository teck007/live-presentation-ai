<template>
  <article class="flex h-full min-h-full flex-col items-center justify-center overflow-hidden bg-slate-900 p-8 text-center text-white md:p-12">
    <p v-if="kicker" class="line-clamp-1 text-sm font-semibold uppercase tracking-widest text-emerald-400">{{ kicker }}</p>
    <h3 class="mt-2 line-clamp-2 text-4xl font-bold tracking-tight md:text-5xl">{{ title }}</h3>
    <p v-if="subtitle" class="mt-4 line-clamp-3 max-w-2xl text-lg leading-relaxed text-slate-300">{{ subtitle }}</p>
    <p v-else-if="text" class="mt-4 line-clamp-3 max-w-2xl text-lg leading-relaxed text-slate-300">{{ text }}</p>
  </article>
</template>

<script setup lang="ts">
// Hero cover: centered opening or topic-change slide, no list content.
defineProps<{
  title: string;
  text: string;
  kicker?: string;
  subtitle?: string;
  keywords?: string[];
  bullets?: string[];
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  code?: string;
  image?: string;
}>();
</script>
