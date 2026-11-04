<template>
  <article class="flex h-full min-h-full flex-col items-center justify-center overflow-hidden rounded-none border-l-8 border-[var(--accent,var(--slide-accent))] bg-[var(--base,var(--slide-base))] p-10 text-center text-[var(--text,var(--slide-text))]">
    <p class="line-clamp-1 kicker">{{ title }}</p>
    <blockquote class="mt-4 line-clamp-4 h-slide">
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
