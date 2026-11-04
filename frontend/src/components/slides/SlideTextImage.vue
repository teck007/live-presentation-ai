<template>
  <article class="grid h-full min-h-full gap-6 overflow-hidden rounded-none bg-gradient-to-br from-indigo-900 to-slate-900 p-8 text-left text-white md:grid-cols-2 md:p-12">
    <div class="flex min-h-0 flex-col justify-center">
      <h3 class="line-clamp-2 text-3xl font-bold tracking-tight md:text-4xl">{{ title }}</h3>
      <p class="mt-4 line-clamp-5 text-lg leading-relaxed text-slate-200">{{ text }}</p>
    </div>
    <div
      class="relative flex min-h-32 flex-col items-center justify-center overflow-hidden rounded-xl bg-white/10 text-center"
      :class="{ 'animate-pulse': hasImage && !loaded }"
      role="img"
      aria-label="Imagen ilustrativa"
    >
      <img
        v-if="hasImage"
        :src="image"
        alt="Imagen ilustrativa del slide"
        loading="lazy"
        fetchpriority="high"
        class="slide-img absolute inset-0 h-full w-full object-cover"
        :class="{ 'is-loaded': loaded }"
        @load="onLoad"
      />
      <template v-else>
        <span class="text-5xl" aria-hidden="true">🖼️</span>
        <p class="mt-3 p-6 pb-0 text-sm text-slate-300">Imagen ilustrativa</p>
        <p class="p-6 pt-1 text-xs text-slate-400">Placeholder MVP — foto real fuera de alcance</p>
      </template>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

// Slide layout: fills the 16:9 stage, content vertically centered.
const props = defineProps<{
  title: string;
  text: string;
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
  bullets?: string[];
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  code?: string;
  image?: string;
}>();

const loaded = ref(false);

const hasImage = computed(
  () => typeof props.image === "string" && props.image.startsWith("https://"),
);

function onLoad() {
  loaded.value = true;
}
</script>

<style scoped>
.slide-img {
  opacity: 0;
  transition: opacity 0.4s ease;
}
.slide-img.is-loaded {
  opacity: 1;
}
</style>
