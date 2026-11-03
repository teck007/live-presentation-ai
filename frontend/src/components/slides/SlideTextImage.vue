<template>
  <article class="grid h-full min-h-full gap-6 overflow-hidden rounded-none bg-gradient-to-br from-indigo-900 to-slate-900 p-8 text-left text-white md:grid-cols-2 md:p-12">
    <div class="flex min-h-0 flex-col justify-center">
      <h3 class="line-clamp-2 text-3xl font-bold tracking-tight md:text-4xl">{{ title }}</h3>
      <p class="mt-4 line-clamp-5 text-lg leading-relaxed text-slate-200">{{ text }}</p>
    </div>
    <div
      class="flex min-h-32 flex-col items-center justify-center overflow-hidden rounded-xl bg-white/10 p-6 text-center"
      role="img"
      aria-label="Imagen ilustrativa pendiente"
    >
      <span class="text-5xl" aria-hidden="true">🖼️</span>
      <p class="mt-3 text-sm text-slate-300">Imagen ilustrativa</p>
      <p class="text-xs text-slate-400">Placeholder MVP — foto real fuera de alcance</p>
    </div>
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
