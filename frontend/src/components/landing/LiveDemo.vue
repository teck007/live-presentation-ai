<template>
  <div
    class="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl dark:border-white/10 dark:bg-slate-900"
    :aria-label="t('landing.demoLabel')"
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
    <!-- Simulated slide -->
    <div class="aspect-video w-full">
      <SlideTitleText :title="activeSlide.title" :text="activeSlide.text" />
    </div>
    <div class="flex items-center justify-between px-4 py-3">
      <div class="flex gap-1.5" aria-hidden="true">
        <span
          v-for="(turn, index) in turns"
          :key="turn.title"
          class="h-1.5 rounded-full transition-all"
          :class="index === turnIndex ? 'w-8 bg-emerald-500' : 'w-4 bg-slate-300 dark:bg-white/20'"
        ></span>
      </div>
      <p class="text-xs text-slate-500 dark:text-slate-400">{{ t("landing.demoNote") }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import SlideTitleText from "../slides/SlideTitleText.vue";

interface DemoTurn {
  transcript: string;
  title: string;
  text: string;
}

const { t } = useI18n({ useScope: "global" });

// Demo catalog: copy lives in locales (es/en), so the switch re-renders.
const turns = computed<DemoTurn[]>(() => [
  {
    transcript: t("landing.demo.t1.transcript"),
    title: t("landing.demo.t1.title"),
    text: t("landing.demo.t1.text"),
  },
  {
    transcript: t("landing.demo.t2.transcript"),
    title: t("landing.demo.t2.title"),
    text: t("landing.demo.t2.text"),
  },
  {
    transcript: t("landing.demo.t3.transcript"),
    title: t("landing.demo.t3.title"),
    text: t("landing.demo.t3.text"),
  },
]);

const turnIndex = ref(0);
const visibleTranscript = ref("");
const isTyping = ref(true);
const activeSlide = ref({ title: turns.value[0].title, text: turns.value[0].text });

let intervalId: number | null = null;
let holdId: number | null = null;

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

function playTurn(index: number): void {
  clearTimers();
  const list = turns.value;
  turnIndex.value = index;
  activeSlide.value = { title: list[index].title, text: list[index].text };
  visibleTranscript.value = "";
  isTyping.value = true;
  let charPos = 0;
  intervalId = window.setInterval(() => {
    charPos += 2;
    visibleTranscript.value = list[index].transcript.slice(0, charPos);
    if (charPos >= list[index].transcript.length) {
      if (intervalId !== null) window.clearInterval(intervalId);
      intervalId = null;
      isTyping.value = false;
      holdId = window.setTimeout(() => {
        playTurn((index + 1) % list.length);
      }, 2200);
    }
  }, 40);
}

onMounted(() => {
  const reduceMotion =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) {
    clearTimers();
    visibleTranscript.value = turns.value[0].transcript;
    isTyping.value = false;
    turnIndex.value = 0;
    activeSlide.value = { title: turns.value[0].title, text: turns.value[0].text };
    return;
  }
  playTurn(0);
});

onBeforeUnmount(() => clearTimers());
</script>
