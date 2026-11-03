<template>
  <section class="text-left" aria-live="polite">
    <div v-if="error" class="mb-3 rounded-2xl bg-red-500/15 p-3 text-sm text-red-200" role="alert">
      {{ error }}
    </div>

    <!-- Empty state -->
    <div v-if="!slides.length" class="mx-auto w-full max-w-5xl">
      <div class="flex aspect-video w-full flex-col items-center justify-center rounded-3xl border border-dashed border-white/15 bg-white/5 p-8 text-center shadow-2xl">
        <span class="text-5xl" aria-hidden="true">📊</span>
        <p class="mt-4 text-lg font-semibold text-white">Aún no hay slides</p>
        <p class="mt-1 max-w-md text-sm text-slate-400">
          Los slides aparecerán aquí a medida que hables. El diseño lo elige el LLM (solo id de layout).
        </p>
        <span v-if="pending" class="mt-4 rounded-full bg-blue-500/20 px-4 py-1.5 text-sm text-blue-200">Generando slide…</span>
      </div>
    </div>

    <!-- Single 16:9 stage -->
    <div v-else class="mx-auto w-full max-w-5xl">
      <div
        ref="stageRef"
        class="relative aspect-video w-full overflow-hidden rounded-3xl bg-slate-900 shadow-2xl ring-1 ring-white/10"
        :style="stagePaletteStyle"
      >
        <span
          class="absolute left-4 top-4 z-10 rounded-full bg-black/60 px-3 py-1 font-mono text-xs text-emerald-300 backdrop-blur"
        >layout: {{ activeSlide.layout }}</span>
        <Transition name="slide" mode="out-in">
          <div
            v-if="activeSlide.html && activeSlide.html.trim()"
            :key="activeSlide.id + '-html'"
            class="slide-rendered"
            v-html="activeSlide.html"
          ></div>
          <component
            v-else
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
        </Transition>

        <span
          v-if="pending"
          class="absolute right-4 top-4 rounded-full bg-blue-600/90 px-4 py-1.5 text-sm font-medium text-white shadow-lg"
          role="status"
        >
          Generando slide…
        </span>

        <!-- Arrows -->
        <button
          type="button"
          aria-label="Slide anterior"
          class="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2.5 text-white backdrop-blur transition hover:bg-black/70 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!canPrev"
          @click="prev"
        >
          <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M12.5 4 7 10l5.5 6 1.5-1.4L9.9 10l4.1-4.6L12.5 4Z"/></svg>
        </button>
        <button
          type="button"
          aria-label="Slide siguiente"
          class="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-black/50 p-2.5 text-white backdrop-blur transition hover:bg-black/70 disabled:cursor-not-allowed disabled:opacity-40"
          :disabled="!canNext"
          @click="next"
        >
          <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7.5 4 13 10l-5.5 6L6 14.6 10.1 10 6 5.4 7.5 4Z"/></svg>
        </button>
      </div>

      <!-- Counter + fullscreen -->
      <div class="mt-3 flex items-center justify-between">
        <p class="text-sm text-slate-400" aria-live="polite">{{ activeIndex + 1 }} / {{ slides.length }}</p>
        <button
          type="button"
          class="rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-slate-300 transition hover:bg-white/10"
          @click="toggleFullscreen"
        >
          Pantalla completa
        </button>
      </div>

      <!-- Thumbnails -->
      <div class="mt-2 flex gap-2 overflow-x-auto pb-1" role="listbox" aria-label="Slides">
        <button
          v-for="(slide, i) in slides"
          :key="slide.id"
          type="button"
          role="option"
          :aria-selected="i === activeIndex"
          :title="slide.title"
          class="max-w-44 shrink-0 truncate rounded-xl border px-3 py-2 text-left text-xs transition"
          :class="i === activeIndex ? 'border-emerald-400 bg-emerald-500/15 text-emerald-100' : 'border-white/10 bg-white/5 text-slate-400 hover:bg-white/10'"
          @click="goTo(i)"
        >
          <span class="mr-1 font-semibold">{{ i + 1 }}.</span>{{ slide.title }}
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import type { SlideItem, SlideLayoutId } from "../types";
import { SLIDE_LAYOUTS } from "./slides/slideLayouts";

const props = defineProps<{ slides: SlideItem[]; pending: boolean; error: string | null }>();

// Single-stage view: show one 16:9 slide, auto-jump to latest on push.
const activeIndex = ref(0);
const stageRef = ref<HTMLElement | null>(null);

const activeSlide = computed(() => props.slides[activeIndex.value] ?? props.slides[props.slides.length - 1]);
const canPrev = computed(() => activeIndex.value > 0);
const canNext = computed(() => activeIndex.value < props.slides.length - 1);

// Palette theming for the Vue fallback: map palette roles to CSS vars.
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
    // New slide pushed -> force jump to latest. Filtered turns push nothing -> no jump.
    if (n > old) activeIndex.value = n - 1;
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
  if (e.key === "ArrowLeft") prev();
  else if (e.key === "ArrowRight") next();
}

onMounted(() => window.addEventListener("keydown", onKeydown));
onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown));

function layoutComponent(layout: SlideLayoutId) {
  return SLIDE_LAYOUTS[layout]?.component ?? SLIDE_LAYOUTS.title_text.component;
}
</script>
