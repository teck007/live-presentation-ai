<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:p-12">
    <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
    <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
    <div class="rule" aria-hidden="true"></div>
    <div :class="['mt-6 grid min-h-0 gap-4 overflow-hidden', gridClass]" :data-density="stats.length >= 4 ? 'high' : null">
      <div
        v-for="(stat, i) in stats.slice(0, 4)"
        :key="i"
        class="card min-h-0 overflow-hidden text-center"
      >
        <p class="line-clamp-1 stat-value">{{ statValue(stat) }}</p>
        <p class="mt-1 line-clamp-2 muted">{{ statLabel(stat) }}</p>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { SlideStat } from "../../types";

// Flexible stats grid: 2-4 metrics, static Tailwind grid classes only.
const props = defineProps<{
  title: string;
  text: string;
  kicker?: string;
  stats?: (SlideStat | string)[];
  keywords?: string[];
}>();

const stats = computed(() => props.stats ?? []);
const gridClass = computed(() => {
  const n = Math.min(4, Math.max(2, stats.value.length || 2));
  if (n === 2) return "md:grid-cols-2";
  if (n === 3) return "md:grid-cols-3";
  return "md:grid-cols-2 xl:grid-cols-4";
});

function statValue(stat: SlideStat | string): string {
  return typeof stat === "string" ? stat : (stat.value ?? "");
}

function statLabel(stat: SlideStat | string): string {
  return typeof stat === "string" ? "" : (stat.label ?? props.text ?? "");
}
</script>
