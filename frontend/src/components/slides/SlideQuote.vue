<template>
  <article class="flex h-full min-h-full flex-col items-center justify-center overflow-hidden rounded-none bg-amber-50 p-10 text-center">
    <p class="line-clamp-1 text-sm font-semibold uppercase tracking-widest text-amber-600">{{ title }}</p>
    <blockquote class="mt-4 line-clamp-4 text-2xl font-medium italic leading-relaxed text-slate-900 md:text-3xl">
      “{{ text }}”
    </blockquote>
  </article>
</template>

<script setup lang="ts">
// Slide layout: fills the 16:9 stage, content vertically centered.
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
