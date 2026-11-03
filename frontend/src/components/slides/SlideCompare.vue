<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-slate-900 p-8 text-left text-white md:p-12">
    <p v-if="kicker" class="line-clamp-1 text-sm font-semibold uppercase tracking-widest text-emerald-400">{{ kicker }}</p>
    <h3 class="line-clamp-2 text-3xl font-bold tracking-tight md:text-4xl">{{ title }}</h3>
    <div class="mt-6 grid min-h-0 gap-4 overflow-hidden md:grid-cols-2">
      <div
        v-for="(card, i) in cards.slice(0, 2)"
        :key="i"
        class="min-h-0 overflow-hidden rounded-xl bg-white/5 p-4 ring-1 ring-white/10"
      >
        <p class="line-clamp-1 text-base font-semibold text-emerald-300">{{ cardTitle(card) }}</p>
        <p class="mt-1 line-clamp-4 text-sm leading-relaxed text-slate-200">{{ cardText(card) }}</p>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { SlideCard } from "../../types";

// Compare layout: exactly 2 cards side by side (vs, pros/cons, before/after).
const props = defineProps<{
  title: string;
  text: string;
  kicker?: string;
  cards?: (SlideCard | string)[];
  keywords?: string[];
}>();

const cards = computed(() => props.cards ?? []);

function cardTitle(card: SlideCard | string): string {
  return typeof card === "string" ? card : (card.title ?? "");
}

function cardText(card: SlideCard | string): string {
  return typeof card === "string" ? "" : (card.text ?? props.text ?? "");
}
</script>
