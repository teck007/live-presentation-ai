<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:p-12">
    <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
    <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
    <div class="rule" aria-hidden="true"></div>
    <ol class="mt-6 max-h-56 space-y-3 overflow-hidden" :data-density="steps.length >= 4 ? 'high' : null">
      <li
        v-for="(step, i) in steps.slice(0, 4)"
        :key="i"
        class="flex items-start gap-3"
      >
        <span class="step-number shrink-0" aria-hidden="true">{{ String(i + 1).padStart(2, "0") }}</span>
        <span class="line-clamp-2 min-w-0 pt-1">{{ stepText(step) }}</span>
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
