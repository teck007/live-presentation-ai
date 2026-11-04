<template>
  <article class="grid h-full min-h-full gap-6 overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:grid-cols-2 md:p-12">
    <div class="flex min-h-0 flex-col justify-center overflow-hidden">
      <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
      <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
      <div class="rule" aria-hidden="true"></div>
      <p class="line-clamp-5 body-lg">{{ text }}</p>
    </div>
    <pre class="max-h-56 min-h-0 overflow-auto rounded-xl bg-[#101418] p-4 text-left ring-1 ring-black/20 dark:ring-white/10"><code class="whitespace-pre-wrap break-words font-mono text-[calc(clamp(11px,1.2cqi,15px)*var(--slide-user-scale,1))] leading-relaxed text-emerald-200">{{ code }}</code></pre>
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
