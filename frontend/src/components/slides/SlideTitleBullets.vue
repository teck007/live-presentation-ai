<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden rounded-none border border-neutral-200 bg-white p-8 text-left md:p-12">
    <h3 class="line-clamp-2 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">{{ title }}</h3>
    <ul class="mt-4 max-h-56 space-y-2 overflow-hidden">
      <li
        v-for="(b, i) in bullets"
        :key="i"
        class="flex items-start gap-2 text-lg text-slate-700"
      >
        <span class="mt-2 size-2 shrink-0 rounded-full bg-blue-600" aria-hidden="true"></span>
        <span class="line-clamp-2">{{ b }}</span>
      </li>
    </ul>
    <p v-if="!bullets.length" class="mt-4 line-clamp-4 text-lg text-slate-700">{{ text }}</p>
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
