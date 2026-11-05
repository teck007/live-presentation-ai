<template>
  <article class="relative flex h-full min-h-full flex-col items-center justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-center text-[var(--text,var(--slide-text))] md:p-12">
    <img
      v-if="hasImage"
      :src="image"
      :alt="title"
      loading="lazy"
      fetchpriority="high"
      class="slide-img absolute inset-0 h-full w-full object-cover"
      :class="{ 'is-loaded': loaded }"
      @load="onLoad"
      @error="onError"
    />
    <div v-if="hasImage" class="absolute inset-0 bg-black/45" aria-hidden="true"></div>
    <div class="relative flex flex-col items-center justify-center text-center">
      <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
      <h3 class="mt-2 line-clamp-2 h-display">{{ title }}</h3>
      <p v-if="subtitle" class="mt-4 line-clamp-3 max-w-2xl subtitle">{{ subtitle }}</p>
      <p v-else-if="text" class="mt-4 line-clamp-3 max-w-2xl subtitle">{{ text }}</p>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";

// Hero cover: centered opening or topic-change slide, no list content.
// Renders the generative image as a background when the URL is safe https,
// mirroring the SlideTextImage guard.
const props = defineProps<{
  title: string;
  text: string;
  kicker?: string;
  subtitle?: string;
  keywords?: string[];
  bullets?: string[];
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  code?: string;
  image?: string;
}>();

const loaded = ref(false);
const failed = ref(false);

// Local Vite-bundled assets ("/…", "./…", "../…") with an image extension
// and data URIs are allowed alongside remote https URLs. Everything else
// (http, blob, missing extension) is blocked and falls back to no image.
const LOCAL_IMAGE_RE = /\.(webp|png|jpe?g|svg)$/i;

function isAllowedImage(src: unknown): src is string {
  if (typeof src !== "string" || src.length === 0) return false;
  if (src.startsWith("https://")) return true;
  if (src.startsWith("data:image/")) return true;
  const isLocalPath =
    src.startsWith("/") || src.startsWith("./") || src.startsWith("../");
  if (!isLocalPath) return false;
  return LOCAL_IMAGE_RE.test(src.split("?")[0].split("#")[0]);
}

const hasImage = computed(() => !failed.value && isAllowedImage(props.image));

function onLoad() {
  loaded.value = true;
}

function onError() {
  // Broken URL: unmount the img instead of trapping opacity at 0 forever.
  failed.value = true;
}

watch(
  () => props.image,
  () => {
    failed.value = false;
    loaded.value = false;
  },
);
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
