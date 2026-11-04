<template>
  <article class="grid h-full min-h-full gap-6 overflow-hidden rounded-none bg-gradient-to-br from-indigo-100 to-white p-8 text-left text-[var(--text,var(--slide-text))] md:grid-cols-2 md:p-12 dark:from-indigo-950 dark:to-slate-900 dark:text-[var(--text,var(--slide-text))]">
    <div class="flex min-h-0 flex-col justify-center">
      <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
      <h3 class="line-clamp-2 h-slide">{{ title }}</h3>
      <div class="rule" aria-hidden="true"></div>
      <p class="line-clamp-5 body-lg">{{ text }}</p>
    </div>
    <div
      class="relative flex min-h-32 flex-col items-center justify-center overflow-hidden rounded-xl bg-slate-900/5 text-center ring-1 ring-black/10 dark:bg-white/10 dark:ring-white/10"
      :class="{ 'animate-pulse': hasImage && !loaded }"
      role="img"
      :aria-label="t('live.canvas.decoImage')"
    >
      <img
        v-if="hasImage"
        :src="image"
        :alt="t('live.canvas.decoImageAlt')"
        loading="lazy"
        fetchpriority="high"
        class="slide-img absolute inset-0 h-full w-full object-cover"
        :class="{ 'is-loaded': loaded }"
        @load="onLoad"
      />
      <template v-else>
        <span class="text-5xl" aria-hidden="true">🖼️</span>
        <p class="mt-3 p-6 pb-0 muted">{{ t("live.canvas.decoImage") }}</p>
        <p class="p-6 pt-1 muted">{{ t("live.canvas.decoPlaceholderNote") }}</p>
      </template>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";

// Slide layout: fills the 16:9 stage, content vertically centered.
// Only the decorative image chrome is translated; title/text/image props
// are model or user content and stay untouched.
const { t } = useI18n({ useScope: "global" });
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
