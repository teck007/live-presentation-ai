<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden rounded-none bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:p-12">
    <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
    <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
    <div class="rule" aria-hidden="true"></div>
    <p class="line-clamp-5 body-lg">{{ text }}</p>
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
