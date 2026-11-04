<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden rounded-none border border-slate-200 bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:p-12 dark:border-white/10">
    <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
    <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
    <div class="rule" aria-hidden="true"></div>
    <ul class="mt-4 max-h-56 space-y-2 overflow-hidden" :data-density="bullets.length >= 4 ? 'high' : null">
      <li
        v-for="(b, i) in bullets"
        :key="i"
        class="flex items-start gap-2"
      >
        <span class="mt-2 size-2 shrink-0 rounded-full bg-[var(--accent,var(--slide-accent))]" aria-hidden="true"></span>
        <span class="line-clamp-2">{{ b }}</span>
      </li>
    </ul>
    <p v-if="!bullets.length" class="line-clamp-4 body-lg">{{ text }}</p>
  </article>
</template>

<script setup lang="ts">
// Slide layout: fills the 16:9 stage, content vertically centered.
defineProps<{
  title: string;
  text: string;
  bullets: string[];
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
  cards?: unknown;
  stats?: unknown;
  chips?: string[];
  steps?: unknown;
  code?: string;
  image?: string;
}>();
</script>
