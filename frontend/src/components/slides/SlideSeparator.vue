<template>
  <article class="flex h-full min-h-full flex-col items-center justify-center overflow-hidden bg-slate-900 p-8 text-center text-white md:p-12">
    <span class="h-1 w-16 rounded-full bg-emerald-400" aria-hidden="true"></span>
    <h3 class="mt-4 line-clamp-2 text-3xl font-bold tracking-tight md:text-4xl">{{ title }}</h3>
    <p v-if="text" class="mt-3 line-clamp-3 max-w-xl text-lg text-slate-300">{{ text }}</p>
  </article>
</template>

<script setup lang="ts">
// Separator: full-bleed minimal break for pauses or section changes.
defineProps<{
  title: string;
  text: string;
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
  bullets?: string[];
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  code?: string;
  image?: string;
}>();
</script>
