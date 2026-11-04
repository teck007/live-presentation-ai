<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:p-12">
    <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
    <div class="rule" aria-hidden="true"></div>
    <div class="mt-6 flex max-h-56 flex-wrap content-start gap-2 overflow-hidden" :data-density="chips.length >= 4 ? 'high' : null">
      <span
        v-for="(chip, i) in chips.slice(0, 4)"
        :key="i"
        class="line-clamp-1 max-w-full rounded-full bg-[var(--base-2,var(--slide-base-2))] px-4 py-1.5 text-[calc(clamp(12px,1.2cqi,15px)*var(--slide-user-scale,1))] font-medium text-[var(--text-2,var(--slide-text-2))]"
      >{{ chip }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

// Chips layout: short concepts rendered as pills, no long text.
const props = defineProps<{
  title: string;
  text: string;
  chips?: string[];
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
}>();

const chips = computed(() => props.chips ?? []);
</script>
