<template>
  <div
    ref="rootRef"
    tabindex="0"
    class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-white/10 dark:bg-slate-900"
    :aria-label="t('landing.example.label')"
    @mouseenter="hoverPaused = true"
    @mouseleave="hoverPaused = false"
    @focusin="hoverPaused = true"
    @focusout="hoverPaused = false"
    @keydown="onKeydown"
  >
    <!-- Simulated transcript bar -->
    <div class="flex items-center gap-2 border-b border-slate-200 px-4 py-3 dark:border-white/10">
      <span class="relative flex size-2.5" aria-hidden="true">
        <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-75"></span>
        <span class="relative inline-flex size-2.5 rounded-full bg-red-500"></span>
      </span>
      <p class="truncate text-sm italic text-slate-600 dark:text-slate-300" role="status" aria-live="polite">
        {{ visibleTranscript }}<span v-if="isTyping" class="animate-pulse">▍</span>
      </p>
    </div>
    <!-- 16:9 stage with fixed indigo-moderno palette -->
    <div
      class="slide-stage relative aspect-video w-full overflow-hidden bg-[var(--base)] text-[var(--text)]"
      :style="stageStyle"
    >
      <Transition name="slide" mode="out-in">
        <div :key="activeSlide.id" class="slide-rendered" :class="{ 'img-reveal': imageReady }">
          <component :is="activeComponent" v-bind="slideProps" :key="activeSlide.id" />
        </div>
      </Transition>
    </div>
    <!-- Controls -->
    <div class="flex items-center gap-2 px-4 py-3">
      <button
        type="button"
        :aria-label="t('landing.example.prev')"
        class="rounded-full p-2 text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/10"
        @click="goTo(index - 1)"
      >
        <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M12.5 4 7 10l5.5 6 1.5-1.4L9.9 10l4.1-4.6L12.5 4Z" /></svg>
      </button>
      <button
        type="button"
        :aria-label="playing ? t('landing.example.pause') : t('landing.example.play')"
        class="rounded-full p-2 text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/10"
        @click="togglePlay"
      >
        <svg v-if="playing" class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6 4h3v12H6zM11 4h3v12h-3z" /></svg>
        <svg v-else class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6 4l10 6-10 6z" /></svg>
      </button>
      <button
        type="button"
        :aria-label="t('landing.example.next')"
        class="rounded-full p-2 text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-white/10"
        @click="goTo(index + 1)"
      >
        <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7.5 4 13 10l-5.5 6L6 14.6 10.1 10 6 5.4 7.5 4Z" /></svg>
      </button>
      <div class="ml-1 flex flex-1 items-center gap-1.5" role="group" :aria-label="progressLabel">
        <button
          v-for="(slide, i) in slides"
          :key="slide.id"
          type="button"
          :aria-label="t('landing.example.goTo', { n: i + 1 })"
          :aria-current="i === index ? 'true' : undefined"
          class="h-1.5 rounded-full transition-all"
          :class="i === index ? 'w-8 bg-emerald-500' : 'w-4 bg-slate-300 hover:bg-slate-400 dark:bg-white/20 dark:hover:bg-white/30'"
          @click="goTo(i)"
        ></button>
      </div>
      <p class="hidden text-xs tabular-nums text-slate-500 sm:block dark:text-slate-400">{{ progressLabel }}</p>
    </div>
    <p class="border-t border-slate-100 px-4 py-2 text-xs text-slate-500 dark:border-white/5 dark:text-slate-400">
      {{ t("landing.example.note") }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { SLIDE_LAYOUTS } from "../slides/slideLayouts";
import { buildExampleSlides, buildExampleTranscripts } from "./exampleSlides";

const { t } = useI18n({ useScope: "global" });

// Fixed indigo-moderno palette: same roles SlideCanvas maps to CSS vars.
const stageStyle = computed<Record<string, string>>(() => ({
  "--base": "#F6F5FB",
  "--base-2": "#1D1B45",
  "--accent": "#3D3B8E",
  "--accent-2": "#E5636B",
  "--text": "#1A1930",
  "--text-2": "#FFFFFF",
  "--muted": "#6A6685",
}));

// Copy resolves via i18n keys so the language switch re-renders.
const slides = computed(() => buildExampleSlides((key: string) => t(key)));
const transcripts = computed(() => buildExampleTranscripts((key: string) => t(key)));

const index = ref(0);
const visibleTranscript = ref("");
const isTyping = ref(true);
const playing = ref(true);
const hoverPaused = ref(false);
const inView = ref(true);
const reducedMotion = ref(false);
// Progressive image reveal: text mounts instantly, the image fades/scales in
// ~600ms later so the slide never blocks on the asset. No motion delay when
// the user prefers reduced motion.
const imageReady = ref(false);
const rootRef = ref<HTMLElement | null>(null);

let intervalId: number | null = null;
let holdId: number | null = null;
let imageTimer: number | null = null;
let observer: IntersectionObserver | null = null;

const activeSlide = computed(() => slides.value[index.value] ?? slides.value[0]);
const activeComponent = computed(
  () => SLIDE_LAYOUTS[activeSlide.value.layout]?.component ?? SLIDE_LAYOUTS.title_text.component,
);

// Same explicit prop set SlideCanvas passes to every layout component,
// except image is gated on imageReady for the progressive reveal.
const slideProps = computed(() => ({
  title: activeSlide.value.title,
  text: activeSlide.value.text,
  bullets: activeSlide.value.bullets,
  keywords: activeSlide.value.keywords,
  kicker: activeSlide.value.kicker,
  subtitle: activeSlide.value.subtitle,
  cards: activeSlide.value.cards,
  stats: activeSlide.value.stats,
  chips: activeSlide.value.chips,
  steps: activeSlide.value.steps,
  code: activeSlide.value.code,
  image: imageReady.value ? activeSlide.value.image : undefined,
}));

const progressLabel = computed(() =>
  t("landing.example.progress", { n: index.value + 1, total: slides.value.length }),
);

function clearTimers(): void {
  if (intervalId !== null) {
    window.clearInterval(intervalId);
    intervalId = null;
  }
  if (holdId !== null) {
    window.clearTimeout(holdId);
    holdId = null;
  }
}

function scheduleImageReveal(): void {
  if (imageTimer !== null) window.clearTimeout(imageTimer);
  imageTimer = null;
  imageReady.value = false;
  if (reducedMotion.value) {
    // No staged reveal without motion: show the image with the text.
    imageReady.value = true;
    return;
  }
  imageTimer = window.setTimeout(() => {
    imageTimer = null;
    imageReady.value = true;
  }, 600);
}

function preloadNextImage(current: number): void {
  const total = slides.value.length;
  if (total === 0) return;
  const next = slides.value[((current % total) + total + 1) % total]?.image;
  if (typeof next === "string" && next.length > 0) {
    const pre = new Image();
    pre.src = next;
  }
}

function stepTyping(): void {
  const full = transcripts.value[index.value] ?? "";
  visibleTranscript.value = full.slice(0, visibleTranscript.value.length + 2);
  if (visibleTranscript.value.length >= full.length) {
    if (intervalId !== null) window.clearInterval(intervalId);
    intervalId = null;
    isTyping.value = false;
    scheduleHold();
  }
}

function scheduleHold(): void {
  if (holdId !== null) window.clearTimeout(holdId);
  holdId = window.setTimeout(() => {
    holdId = null;
    goTo(index.value + 1);
  }, 2800);
}

function startTyping(): void {
  if (intervalId !== null) window.clearInterval(intervalId);
  isTyping.value = true;
  intervalId = window.setInterval(stepTyping, 40);
}

function playTurn(i: number): void {
  clearTimers();
  const total = slides.value.length;
  index.value = ((i % total) + total) % total;
  visibleTranscript.value = "";
  startTyping();
}

function showStatic(i: number): void {
  clearTimers();
  const total = slides.value.length;
  index.value = ((i % total) + total) % total;
  visibleTranscript.value = transcripts.value[index.value] ?? "";
  isTyping.value = false;
}

function canAnimate(): boolean {
  return playing.value && !hoverPaused.value && inView.value && !reducedMotion.value;
}

function goTo(i: number): void {
  if (canAnimate()) playTurn(i);
  else showStatic(i);
}

function resume(): void {
  if (!canAnimate()) return;
  const full = transcripts.value[index.value] ?? "";
  if (visibleTranscript.value.length >= full.length) {
    visibleTranscript.value = full;
    isTyping.value = false;
    scheduleHold();
  } else {
    startTyping();
  }
}

function togglePlay(): void {
  playing.value = !playing.value;
  if (!playing.value) {
    clearTimers();
    isTyping.value = false;
  } else {
    resume();
  }
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key === "ArrowLeft") goTo(index.value - 1);
  else if (e.key === "ArrowRight") goTo(index.value + 1);
}

// Pause while hovered/focused or offscreen; resume when conditions clear.
watch([hoverPaused, inView], ([hover, visible]) => {
  if (reducedMotion.value || !playing.value) return;
  if (hover || !visible) {
    clearTimers();
    isTyping.value = false;
  } else {
    resume();
  }
});

// Restage the progressive reveal on every slide turn and warm the next asset
// so image slides fade in without a network stall.
watch(
  () => activeSlide.value.id,
  () => {
    scheduleImageReveal();
    preloadNextImage(index.value);
  },
  { immediate: true },
);

onMounted(() => {
  reducedMotion.value =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion.value) {
    showStatic(0);
    return;
  }
  playTurn(0);
  if (rootRef.value && typeof IntersectionObserver !== "undefined") {
    observer = new IntersectionObserver(
      (entries) => {
        inView.value = entries[0]?.isIntersecting ?? true;
      },
      { threshold: 0.2 },
    );
    observer.observe(rootRef.value);
  }
});

onBeforeUnmount(() => {
  clearTimers();
  if (imageTimer !== null) window.clearTimeout(imageTimer);
  imageTimer = null;
  observer?.disconnect();
  observer = null;
});
</script>

<style scoped>
/* Progressive image reveal: subtle Ken Burns settle once the gated image
 * mounts ~600ms after the text. Killed entirely under reduced motion. */
.img-reveal :deep(img.slide-img) {
  animation: example-img-reveal 0.6s ease-out both;
}
@keyframes example-img-reveal {
  from {
    opacity: 0;
    transform: scale(1.06);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
@media (prefers-reduced-motion: reduce) {
  .img-reveal :deep(img.slide-img) {
    animation: none;
  }
}
</style>
