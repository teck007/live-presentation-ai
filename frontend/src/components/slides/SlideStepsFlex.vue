<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-slate-900 p-8 text-left text-white md:p-12">
    <p v-if="kicker" class="line-clamp-1 text-sm font-semibold uppercase tracking-widest text-emerald-400">{{ kicker }}</p>
    <h3 class="line-clamp-2 text-3xl font-bold tracking-tight md:text-4xl">{{ title }}</h3>
    <ol class="mt-6 max-h-56 space-y-3 overflow-hidden">
      <li
        v-for="(step, i) in steps.slice(0, 4)"
        :key="i"
        class="flex items-start gap-3"
      >
        <span
          class="flex size-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-sm font-bold text-emerald-300 ring-1 ring-emerald-400/30"
          aria-hidden="true"
        >{{ i + 1 }}</span>
        <span class="line-clamp-2 min-w-0 pt-1 text-lg text-slate-200">{{ stepText(step) }}</span>
      </li>
    </ol>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { SlideCard } from "../../types";

// Flexible ordered steps: 2-4 items in sequence.
const props = defineProps<{
  title: string;
  text: string;
  kicker?: string;
  steps?: (string | SlideCard)[];
  keywords?: string[];
}>();

const steps = computed(() => props.steps ?? []);

function stepText(step: string | SlideCard): string {
  if (typeof step === "string") return step;
  return step.text || step.title || props.text || "";
}
</script>
