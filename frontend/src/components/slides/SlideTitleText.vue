<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden rounded-none bg-slate-900 p-8 text-left text-white md:p-12">
    <h3 class="line-clamp-2 text-3xl font-bold tracking-tight md:text-4xl">{{ title }}</h3>
    <p class="mt-4 line-clamp-5 text-lg leading-relaxed text-slate-200">{{ text }}</p>
  </article>
</template>

<script setup lang="ts">
// Slide layout: fills the 16:9 stage, content vertically centered.
// keywords se mantiene en tipos por compat, pero no se muestra en MVP.
defineProps<{
  title: string;
  text: string;
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  code?: string;
  image?: string;
}>();
</script>
