<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-white p-8 text-left md:p-12">
    <h3 class="line-clamp-2 text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">{{ title }}</h3>
    <ul class="mt-4 max-h-56 space-y-2 overflow-hidden">
      <li
        v-for="(item, i) in bullets.slice(0, 4)"
        :key="i"
        class="flex items-start gap-3 text-lg text-slate-700"
      >
        <span
          class="flex size-6 shrink-0 items-center justify-center rounded-md border border-emerald-600 text-sm font-bold text-emerald-600"
          aria-hidden="true"
        >✓</span>
        <span class="line-clamp-2 min-w-0">{{ item }}</span>
      </li>
    </ul>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";

// Checklist layout: tasks or requirements with checkbox markers.
const props = defineProps<{
  title: string;
  text: string;
  bullets?: string[];
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
}>();

const bullets = computed(() => props.bullets ?? []);
</script>
