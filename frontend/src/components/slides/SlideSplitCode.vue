<template>
  <article class="grid h-full min-h-full gap-6 overflow-hidden bg-slate-900 p-8 text-left text-white md:grid-cols-2 md:p-12">
    <div class="flex min-h-0 flex-col justify-center overflow-hidden">
      <p v-if="kicker" class="line-clamp-1 text-sm font-semibold uppercase tracking-widest text-emerald-400">{{ kicker }}</p>
      <h3 class="line-clamp-2 text-3xl font-bold tracking-tight md:text-4xl">{{ title }}</h3>
      <p class="mt-4 line-clamp-5 text-lg leading-relaxed text-slate-200">{{ text }}</p>
    </div>
    <pre class="max-h-56 min-h-0 overflow-auto rounded-xl bg-black/60 p-4 text-left ring-1 ring-white/10"><code class="whitespace-pre-wrap break-words font-mono text-sm leading-relaxed text-emerald-200">{{ code }}</code></pre>
  </article>
</template>

<script setup lang="ts">
// Split code: explanation on the left, real code snippet on the right.
defineProps<{
  title: string;
  text: string;
  code?: string;
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
  bullets?: string[];
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  image?: string;
}>();
</script>
