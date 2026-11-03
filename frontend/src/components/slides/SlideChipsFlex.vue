<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-white p-8 text-left md:p-12">
    <h3 class="line-clamp-2 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">{{ title }}</h3>
    <div class="mt-6 flex max-h-56 flex-wrap content-start gap-2 overflow-hidden">
      <span
        v-for="(chip, i) in chips.slice(0, 4)"
        :key="i"
        class="line-clamp-1 max-w-full rounded-full bg-slate-900 px-4 py-1.5 text-sm font-medium text-white"
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
