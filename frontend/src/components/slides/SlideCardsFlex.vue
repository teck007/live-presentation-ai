<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:p-12">
    <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
    <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
    <div class="rule" aria-hidden="true"></div>
    <div :class="['mt-6 grid min-h-0 gap-4 overflow-hidden', gridClass]" :data-density="cards.length >= 4 ? 'high' : null">
      <div
        v-for="(card, i) in cards.slice(0, 4)"
        :key="i"
        class="card min-h-0 overflow-hidden"
      >
        <p class="line-clamp-1 kicker">{{ cardTitle(card) }}</p>
        <p class="mt-1 line-clamp-3 body-lg">{{ cardText(card) }}</p>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { SlideCard } from "../../types";

// Flexible cards grid: 2-4 items, static Tailwind grid classes only.
const props = defineProps<{
  title: string;
  text: string;
  kicker?: string;
  cards?: (SlideCard | string)[];
  keywords?: string[];
}>();

const cards = computed(() => props.cards ?? []);
const gridClass = computed(() => {
  const n = Math.min(4, Math.max(2, cards.value.length || 2));
  if (n === 2) return "md:grid-cols-2";
  if (n === 3) return "md:grid-cols-3";
  return "md:grid-cols-2 xl:grid-cols-4";
});

function cardTitle(card: SlideCard | string): string {
  return typeof card === "string" ? card : (card.title ?? "");
}

function cardText(card: SlideCard | string): string {
  return typeof card === "string" ? "" : (card.text ?? props.text ?? "");
}
</script>
