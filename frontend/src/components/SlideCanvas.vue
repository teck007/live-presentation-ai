<template>
  <section id="lienzo" tabindex="-1" class="text-left" :aria-label="t('live.canvas.label')">
    <div v-if="error" class="mb-3 flex flex-wrap items-center gap-3 rounded-2xl bg-red-500/10 p-3 text-sm text-red-700 dark:bg-red-500/15 dark:text-red-200" role="alert">
      <span class="flex-1">{{ error }}</span>
      <button
        type="button"
        class="rounded-xl border border-red-500/30 bg-white/60 px-3 py-1.5 text-sm font-medium text-red-700 transition hover:bg-white dark:bg-white/5 dark:text-red-200 dark:hover:bg-white/10"
        @click="emit('retry')"
      >
        {{ t("live.canvas.retry") }}
      </button>
    </div>
    <div v-if="lastFiltered" class="mb-3 rounded-2xl bg-amber-500/10 p-3 text-sm text-amber-800 dark:bg-amber-500/15 dark:text-amber-200" role="status">
      {{ t("live.canvas.offTopic") }}
    </div>

    <!-- Empty state / skeleton -->
    <div v-if="!slides.length" class="mx-auto w-full max-w-5xl">
      <div
        v-if="pending"
        class="flex aspect-video w-full flex-col justify-center gap-4 rounded-3xl border border-slate-200 bg-white p-8 shadow-2xl dark:border-white/10 dark:bg-white/5"
        role="status"
        :aria-label="t('live.canvas.generatingSlide')"
      >
        <div class="h-6 w-2/5 animate-pulse rounded-lg bg-slate-500/15 dark:bg-white/10"></div>
        <div class="h-10 w-4/5 animate-pulse rounded-xl bg-slate-500/15 dark:bg-white/10"></div>
        <div class="h-4 w-3/5 animate-pulse rounded-lg bg-slate-500/15 dark:bg-white/10"></div>
        <span class="mt-2 w-fit rounded-full bg-blue-500/10 px-4 py-1.5 text-sm text-blue-800 dark:bg-blue-500/15 dark:text-blue-200">{{ t("live.canvas.generatingBadge") }}</span>
      </div>
      <div v-else class="flex aspect-video w-full flex-col items-center justify-center rounded-3xl border border-dashed border-slate-300 bg-slate-500/5 p-8 text-center shadow-2xl dark:border-white/15 dark:bg-white/5">
        <span class="text-5xl" aria-hidden="true">📊</span>
        <p class="mt-4 text-lg font-semibold text-slate-900 dark:text-white">{{ t("live.canvas.emptyTitle") }}</p>
        <p class="mt-1 max-w-md text-sm text-slate-500 dark:text-slate-400">
          {{ t("live.canvas.emptyText") }}
        </p>
      </div>
    </div>

    <!-- Single 16:9 stage -->
    <div v-else class="mx-auto w-full max-w-5xl">
      <div
        ref="stageRef"
        role="region"
        :aria-label="t('live.canvas.currentSlide')"
        aria-live="polite"
        class="slide-stage relative aspect-video w-full overflow-hidden rounded-3xl bg-[var(--base,var(--slide-base))] text-[var(--text,var(--slide-text))] shadow-2xl ring-1 ring-slate-900/10 dark:ring-white/10"
        :style="stageStyle"
        :data-scale="scalePercent"
      >
        <span
          v-if="isDev"
          class="absolute left-4 top-4 z-10 rounded-full bg-black/60 px-3 py-1 font-mono text-xs text-emerald-300 backdrop-blur"
        >layout: {{ activeSlide.layout }}</span>
        <Transition name="slide" mode="out-in">
          <div
            v-if="activeSlide.html && activeSlide.html.trim()"
            :key="activeSlide.id + '-html'"
            class="slide-rendered"
            v-html="activeSlide.html"
          ></div>
          <div
            v-else
            :key="activeSlide.id + '-fallback'"
            class="slide-rendered"
          >
          <component
            :is="layoutComponent(activeSlide.layout)"
            :key="activeSlide.id"
            :title="activeSlide.title"
            :text="activeSlide.text"
            :bullets="activeSlide.bullets"
            :keywords="activeSlide.keywords"
            :kicker="activeSlide.kicker"
            :subtitle="activeSlide.subtitle"
            :cards="activeSlide.cards"
            :stats="activeSlide.stats"
            :chips="activeSlide.chips"
            :steps="activeSlide.steps"
            :code="activeSlide.code"
            :image="activeSlide.image"
          />
          </div>
        </Transition>

        <span
          v-if="pending"
          class="absolute right-4 top-4 rounded-full bg-blue-600/90 px-4 py-1.5 text-sm font-medium text-white shadow-lg"
          role="status"
        >
          {{ t("live.canvas.generatingBadge") }}
        </span>
        <span
          v-if="activeSlide?.pending"
          class="absolute bottom-4 left-4 z-10 animate-pulse rounded-full bg-amber-500/90 px-3 py-1 text-xs font-medium text-white"
          role="status"
        >
          {{ t("live.canvas.preview") }}
        </span>

        <!-- Arrows -->
        <button
          type="button"
          :aria-label="t('live.canvas.prevSlide')"
          class="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2.5 text-white backdrop-blur transition hover:bg-black/70 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!canPrev"
          @click="prev"
        >
          <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M12.5 4 7 10l5.5 6 1.5-1.4L9.9 10l4.1-4.6L12.5 4Z"/></svg>
        </button>
        <button
          type="button"
          :aria-label="t('live.canvas.nextSlide')"
          class="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2.5 text-white backdrop-blur transition hover:bg-black/70 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!canNext"
          @click="next"
        >
          <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7.5 4 13 10l-5.5 6L6 14.6 10.1 10 6 5.4 7.5 4Z"/></svg>
        </button>

        <!-- Scale controls inside the stage: kept in fullscreen mode -->
        <div
          class="absolute bottom-3 right-3 z-10 flex items-center gap-1 rounded-full bg-black/50 px-2 py-1 text-sm text-white backdrop-blur"
          role="group"
          :aria-label="t('live.canvas.scaleLabel')"
        >
          <button
            type="button"
            :aria-label="t('live.canvas.scaleDecrease')"
            :title="t('live.canvas.scaleDecrease')"
            :disabled="!canDecrease"
            class="rounded-full px-2 py-0.5 font-semibold transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40"
            @click="decrease"
          >
            A−
          </button>
          <span
            class="min-w-11 text-center tabular-nums"
            aria-live="polite"
            :aria-label="t('live.canvas.scaleValue', { n: scalePercent })"
          >{{ scalePercent }}%</span>
          <button
            type="button"
            :aria-label="t('live.canvas.scaleIncrease')"
            :title="t('live.canvas.scaleIncrease')"
            :disabled="!canIncrease"
            class="rounded-full px-2 py-0.5 font-semibold transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40"
            @click="increase"
          >
            A+
          </button>
          <button
            type="button"
            :aria-label="t('live.canvas.scaleReset')"
            :title="t('live.canvas.scaleReset')"
            :disabled="!canReset"
            class="rounded-full px-2 py-0.5 transition hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40"
            @click="resetScale"
          >
            ↺
          </button>
        </div>
      </div>

      <!-- Counter + scale + follow-live + fullscreen -->
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <p class="text-sm text-slate-500 dark:text-slate-400">{{ activeIndex + 1 }} / {{ slides.length }}</p>
        <label class="inline-flex cursor-pointer items-center gap-2 text-sm text-slate-600 dark:text-slate-300">
          <input type="checkbox" v-model="followLive" class="size-4 accent-emerald-500" />
          {{ t("live.canvas.followLive") }}
        </label>
        <div
          class="ml-auto flex items-center gap-1 rounded-xl border border-slate-300 bg-white px-1.5 py-1 text-sm text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
          role="group"
          :aria-label="t('live.canvas.scaleLabel')"
        >
          <button
            type="button"
            :aria-label="t('live.canvas.scaleDecrease')"
            :title="t('live.canvas.scaleDecrease')"
            :disabled="!canDecrease"
            class="rounded-lg px-2 py-0.5 font-semibold transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-white/10"
            @click="decrease"
          >
            A−
          </button>
          <span
            class="min-w-11 text-center tabular-nums"
            aria-live="polite"
            :aria-label="t('live.canvas.scaleValue', { n: scalePercent })"
          >{{ scalePercent }}%</span>
          <button
            type="button"
            :aria-label="t('live.canvas.scaleIncrease')"
            :title="t('live.canvas.scaleIncrease')"
            :disabled="!canIncrease"
            class="rounded-lg px-2 py-0.5 font-semibold transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-white/10"
            @click="increase"
          >
            A+
          </button>
          <button
            type="button"
            :aria-label="t('live.canvas.scaleReset')"
            :title="t('live.canvas.scaleReset')"
            :disabled="!canReset"
            class="rounded-lg px-2 py-0.5 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40 dark:hover:bg-white/10"
            @click="resetScale"
          >
            ↺
          </button>
        </div>
        <button
          type="button"
          class="rounded-xl border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-600 transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
          @click="toggleFullscreen"
        >
          {{ t("live.canvas.fullscreen") }}
        </button>
      </div>

      <!-- Thumbnails -->
      <ul class="mt-2 flex gap-2 overflow-x-auto pb-1" :aria-label="t('live.canvas.slidesLabel')">
        <li v-for="(slide, i) in slides" :key="slide.id" class="shrink-0">
          <button
            type="button"
            :title="slide.title"
            :aria-current="i === activeIndex ? 'true' : undefined"
            :aria-label="t('live.canvas.goToSlide', { n: i + 1, title: slide.title })"
            class="max-w-44 truncate rounded-xl border px-3 py-2 text-left text-xs transition"
            :class="i === activeIndex ? 'border-emerald-400 bg-emerald-500/15 text-emerald-900 dark:text-emerald-100' : 'border-slate-200 bg-slate-500/5 text-slate-500 hover:bg-slate-500/10 dark:border-white/10 dark:bg-white/5 dark:text-slate-400 dark:hover:bg-white/10'"
            @click="goTo(i)"
          >
            <span class="mr-1 font-semibold">{{ i + 1 }}.</span>{{ slide.title }}
          </button>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { SlideItem, SlideLayoutId } from "../types";
import { SLIDE_LAYOUTS } from "./slides/slideLayouts";

const { t } = useI18n({ useScope: "global" });

const props = defineProps<{ slides: SlideItem[]; pending: boolean; error: string | null; lastFiltered?: boolean; scale?: number }>();

const emit = defineEmits<{ (e: "retry"): void; (e: "update:scale", value: number): void }>();

const isDev = import.meta.env.DEV;

// User text scale (percent, 80-130 step 10): owned by the parent (LiveView),
// applied here as --slide-user-scale on the stage container. Changing it
// never touches slides/activeIndex: no jump, no reorder, no slide event.
const SCALE_MIN = 80;
const SCALE_MAX = 130;
const SCALE_STEP = 10;
const SCALE_DEFAULT = 100;

const scalePercent = computed(() => {
  const raw = props.scale ?? SCALE_DEFAULT;
  if (!Number.isFinite(raw)) return SCALE_DEFAULT;
  return Math.min(SCALE_MAX, Math.max(SCALE_MIN, Math.round(raw)));
});
const canDecrease = computed(() => scalePercent.value > SCALE_MIN);
const canIncrease = computed(() => scalePercent.value < SCALE_MAX);
const canReset = computed(() => scalePercent.value !== SCALE_DEFAULT);

function decrease() {
  if (canDecrease.value) emit("update:scale", scalePercent.value - SCALE_STEP);
}

function increase() {
  if (canIncrease.value) emit("update:scale", scalePercent.value + SCALE_STEP);
}

function resetScale() {
  if (canReset.value) emit("update:scale", SCALE_DEFAULT);
}

// Single-stage view: show one 16:9 slide, auto-jump to latest on push.
const activeIndex = ref(0);
const stageRef = ref<HTMLElement | null>(null);
// Follow live: when on, jump to the newest slide on arrival.
const followLive = ref(true);

const activeSlide = computed(() => props.slides[activeIndex.value] ?? props.slides[props.slides.length - 1]);
const canPrev = computed(() => activeIndex.value > 0);
const canNext = computed(() => activeIndex.value < props.slides.length - 1);

// Palette theming for the Vue fallback: map palette roles to CSS vars,
// plus the user scale factor consumed by the cqi type tokens in style.css.
const stagePaletteStyle = computed<Record<string, string>>(() => {
  const p = activeSlide.value?.palette as Record<string, string> | undefined;
  if (!p) return {};
  const style: Record<string, string> = {};
  if (p.background) style["--base"] = p.background;
  if (p.background_alt) style["--base-2"] = p.background_alt;
  if (p.primary) style["--accent"] = p.primary;
  if (p.secondary) style["--accent-2"] = p.secondary;
  if (p.text) style["--text"] = p.text;
  if (p.text_alt) style["--text-2"] = p.text_alt;
  if (p.muted) style["--muted"] = p.muted;
  return style;
});

const stageStyle = computed<Record<string, string>>(() => ({
  ...stagePaletteStyle.value,
  "--slide-user-scale": String(scalePercent.value / 100),
}));

function clampIndex() {
  if (!props.slides.length) {
    activeIndex.value = 0;
    return;
  }
  if (activeIndex.value > props.slides.length - 1) activeIndex.value = props.slides.length - 1;
  if (activeIndex.value < 0) activeIndex.value = 0;
}

watch(
  () => props.slides.length,
  (n, old) => {
    // New slide: jump to last only when "Follow live" is on.
    if (n > old && followLive.value) activeIndex.value = n - 1;
    else clampIndex();
  },
);

function prev() {
  if (canPrev.value) activeIndex.value -= 1;
}

function next() {
  if (canNext.value) activeIndex.value += 1;
}

function goTo(i: number) {
  activeIndex.value = i;
  clampIndex();
}

function toggleFullscreen() {
  const el = stageRef.value;
  if (!el) return;
  if (document.fullscreenElement) void document.exitFullscreen();
  else void el.requestFullscreen();
}

function onKeydown(e: KeyboardEvent) {
  const target = e.target as HTMLElement | null;
  if (target?.closest?.('input, textarea, select, [contenteditable="true"]')) return;
  if (e.key === "ArrowLeft") prev();
  else if (e.key === "ArrowRight") next();
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));

function layoutComponent(layout: SlideLayoutId) {
  return SLIDE_LAYOUTS[layout]?.component ?? SLIDE_LAYOUTS.title_text.component;
}
</script>
