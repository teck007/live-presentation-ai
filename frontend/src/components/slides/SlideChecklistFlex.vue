<template>
  <article class="flex h-full min-h-full flex-col justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-left text-[var(--text,var(--slide-text))] md:p-12">
    <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
    <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
    <div class="rule" aria-hidden="true"></div>
    <ul class="mt-4 max-h-56 space-y-2 overflow-hidden" :data-density="bullets.length >= 4 ? 'high' : null">
      <li
        v-for="(item, i) in bullets.slice(0, 4)"
        :key="i"
        class="check"
      >
        <span class="icon-badge shrink-0" aria-hidden="true">✓</span>
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
