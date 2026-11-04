<template>
  <aside
    class="flex h-full w-[300px] shrink-0 flex-col gap-5 overflow-y-auto rounded-r-3xl border-r border-slate-200 bg-slate-50/95 p-5 text-slate-800 backdrop-blur dark:border-white/10 dark:bg-slate-900/95 dark:text-slate-200"
  >
    <!-- Status (branding lives in the persistent navbar) -->
    <div class="flex items-center gap-3">
      <p class="text-sm font-semibold text-slate-700 dark:text-slate-300">{{ t("live.sidebar.subtitle") }}</p>
      <span class="ml-auto rounded-full px-3 py-1 text-xs font-medium" :class="statusPillClass" role="status">
        {{ statusLabel }}
      </span>
    </div>

    <!-- Live controls -->
    <section :aria-label="t('live.sidebar.controlsLabel')">
      <h2 class="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">{{ t("live.sidebar.liveSection") }}</h2>
      <div class="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-emerald-900/50 disabled:text-slate-400"
          :disabled="liveActive"
          @click="emit('start-live')"
        >
          <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7 4a3 3 0 0 1 6 0v6a3 3 0 0 1-6 0V4Z"/><path d="M4 10a6 6 0 0 0 12 0h-1.5a4.5 4.5 0 0 1-9 0H4Z"/><path d="M10 16.5v2.5h2v-2.5h-2Z"/></svg>
          {{ t("live.sidebar.start") }}
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-xl bg-slate-500/10 px-4 py-2 text-sm font-medium text-slate-800 transition hover:bg-slate-500/15 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-white/10 dark:text-white dark:hover:bg-white/15"
          :disabled="!liveActive"
          @click="emit('stop-live')"
        >
          <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><rect x="5" y="5" width="10" height="10" rx="2"/></svg>
          {{ t("live.sidebar.stop") }}
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-500 transition hover:text-slate-900 disabled:cursor-not-allowed disabled:opacity-50 dark:text-slate-400 dark:hover:text-white"
          :disabled="clearDisabled"
          @click="emit('clear-live')"
        >
          <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6 4h8l1 2h3v2H2V6h3l1-2Zm-2 6h12l-1 6H5l-1-6Z"/></svg>
          {{ t("live.sidebar.clear") }}
        </button>
      </div>

      <div class="mt-3">
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300" for="presentation-topic">
          {{ t("live.sidebar.topicLabel") }}
        </label>
        <input
          id="presentation-topic"
          :value="presentationTopic"
          type="text"
          :placeholder="t('live.sidebar.topicPlaceholder')"
          aria-describedby="presentation-topic-hint"
          class="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none dark:border-white/10 dark:bg-slate-800 dark:text-white dark:placeholder:text-slate-500"
          @input="emit('update:topic', ($event.target as HTMLInputElement).value)"
        />
        <p id="presentation-topic-hint" class="mt-1 text-xs text-slate-500">
          {{ t("live.sidebar.topicHint") }}
        </p>
        <p class="mt-1 text-xs text-slate-400 dark:text-slate-500">
          {{ t("live.sidebar.coverAutoHint") }}
        </p>
        <p v-if="!presentationTopic.trim()" class="mt-1 rounded-lg bg-amber-500/10 p-2 text-xs text-amber-800 dark:bg-amber-500/15 dark:text-amber-200">
          {{ t("live.sidebar.topicWarning") }}
        </p>
      </div>

      <div class="mt-3">
        <label class="block text-sm font-medium text-slate-700 dark:text-slate-300" for="presentation-audience">
          {{ t("live.sidebar.audienceLabel") }}
        </label>
        <select
          id="presentation-audience"
          :value="presentationAudience"
          class="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 focus:border-emerald-500 focus:outline-none dark:border-white/10 dark:bg-slate-800 dark:text-white"
          @change="emit('update:audience', ($event.target as HTMLSelectElement).value)"
        >
          <option value="ninos">{{ t("live.sidebar.audience.kids") }}</option>
          <option value="estudiantes">{{ t("live.sidebar.audience.students") }}</option>
          <option value="general">{{ t("live.sidebar.audience.general") }}</option>
          <option value="profesionales">{{ t("live.sidebar.audience.professionals") }}</option>
          <option value="expertos">{{ t("live.sidebar.audience.experts") }}</option>
        </select>
        <p class="mt-1 text-xs text-slate-500">
          {{ t("live.sidebar.audienceHint") }}
        </p>
      </div>

      <div v-if="notice" class="mt-3 rounded-xl bg-blue-500/10 p-3 text-sm text-blue-800 dark:bg-blue-500/15 dark:text-blue-200" role="status">
        {{ notice }}
      </div>
      <div v-if="error" class="mt-3 rounded-xl bg-red-500/10 p-3 text-sm text-red-700 dark:bg-red-500/15 dark:text-red-200" role="alert">
        {{ error }}
        <span class="mt-1 block text-red-600 dark:text-red-300">{{ t("live.sidebar.batchHint") }}</span>
      </div>
    </section>

    <!-- Noise controls (collapsed by default) -->
    <details class="rounded-2xl border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-slate-800/60">
      <summary class="cursor-pointer text-sm font-medium text-slate-800 dark:text-slate-200">
        {{ t("live.sidebar.advanced") }}
      </summary>
      <div class="mt-2">
        <p class="inline-flex items-center gap-2 text-sm font-medium text-slate-800 dark:text-slate-200">
          <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M4 6h12v2H4zM4 9h12v2H4zM4 12h7v2H4z"/></svg>
          {{ t("live.sidebar.noiseReduction") }}
        </p>
        <label class="mt-2 flex cursor-pointer items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input
            type="checkbox"
            class="size-4 accent-emerald-500"
            :checked="prefilterEnabled"
            @change="emit('prefilter-enabled', ($event.target as HTMLInputElement).checked)"
          />
          {{ t("live.sidebar.enableFilter") }}
        </label>
        <label class="mt-3 block text-sm text-slate-700 dark:text-slate-300" for="prefilter-threshold">
          {{ t("live.sidebar.closeness") }}
          <span class="block text-xs text-slate-500">{{ t("live.sidebar.closenessHint") }}</span>
          <input
            id="prefilter-threshold"
            type="range"
            min="0.01"
            max="0.05"
            step="0.005"
            class="mt-1 w-full accent-emerald-500"
            :value="prefilterThreshold"
            :disabled="!prefilterEnabled"
            aria-describedby="prefilter-threshold-value"
            @input="emit('prefilter-threshold', Number(($event.target as HTMLInputElement).value))"
          />
          <span id="prefilter-threshold-value" class="mt-1 block text-xs text-slate-500">{{ t("live.sidebar.value", { v: prefilterThreshold.toFixed(3) }) }}</span>
        </label>
        <div class="mt-2 flex items-center gap-2">
          <span class="text-xs text-slate-500">{{ t("live.sidebar.level") }}</span>
          <div
            class="h-2 flex-1 overflow-hidden rounded-full bg-slate-500/15 dark:bg-white/10"
            role="meter"
            :aria-label="t('live.sidebar.micLevel')"
            aria-valuemin="0"
            aria-valuemax="100"
            :aria-valuenow="Math.min(100, Math.round(prefilterLevel * 400))"
          >
            <div
              class="h-full rounded-full bg-emerald-500 transition-[width]"
              :style="{ width: `${Math.min(100, Math.round(prefilterLevel * 400))}%` }"
            ></div>
          </div>
        </div>
      </div>
    </details>

    <!-- Live transcript summary -->
    <section :aria-label="t('live.sidebar.transcriptLabel')">
      <h2 class="text-xs font-semibold uppercase tracking-widest text-slate-500 dark:text-slate-400">{{ t("live.sidebar.transcriptLabel") }}</h2>
      <div
        v-if="partialText"
        class="mt-2 rounded-xl border-l-4 border-blue-400 bg-blue-500/10 p-3 text-left text-sm italic text-slate-700 dark:bg-blue-500/15 dark:text-slate-300"
        role="status"
      >
        {{ partialText }}<span class="animate-pulse">…</span>
      </div>
      <p v-else-if="liveActive" class="mt-2 text-sm text-slate-500">
        {{ serverPaused ? t("live.sidebar.pausedEmpty") : t("live.sidebar.listeningEmpty") }}
      </p>
      <ul v-if="finalItems.length > 0" class="mt-2 max-h-48 space-y-2 overflow-y-auto text-left">
        <li
          v-for="(item, index) in finalItems"
          :key="`${item.sessionId ?? 'turn'}-${index}`"
          class="rounded-xl bg-emerald-500/10 p-3 text-sm text-emerald-900 dark:text-emerald-100"
        >
          <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">{{ t("live.sidebar.complete") }}</p>
          {{ item.text }}
          <div v-if="item.keywords?.length" class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="(keyword, kindex) in item.keywords"
              :key="`${keyword}-${kindex}`"
              class="rounded-full bg-slate-900/5 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-white/10 dark:text-slate-300"
            >
              {{ keyword }}
            </span>
          </div>
        </li>
      </ul>
      <p v-if="lastFiltered" class="mt-2 rounded-lg bg-amber-500/10 p-2 text-xs text-amber-800 dark:bg-amber-500/15 dark:text-amber-200" role="status">
        {{ t("live.sidebar.offTopicShort") }}
      </p>
    </section>

    <!-- Batch recorder (collapsed by default) -->
    <details class="rounded-2xl border border-slate-200 bg-white p-3 dark:border-white/10 dark:bg-slate-800/60">
      <summary class="cursor-pointer text-sm font-semibold text-slate-800 dark:text-slate-200">
        {{ t("live.sidebar.batchTitle") }}
      </summary>
      <p class="mt-1 text-xs text-slate-500">
        {{ t("live.sidebar.batchText") }}
      </p>
      <div class="mt-2">
        <slot name="recorder" />
      </div>
      <button
        type="button"
        class="mt-2 w-full rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-blue-900/50 disabled:text-slate-400"
        :disabled="!canTranscribe"
        @click="emit('batch-transcribe')"
      >
        {{ batchLoading ? t("live.sidebar.transcribing") : t("live.sidebar.transcribe") }}
      </button>
      <div v-if="batchLoading" class="mt-2 flex items-center justify-center gap-2 text-sm text-slate-600 dark:text-slate-300" role="status">
        <span class="inline-block size-[16px] animate-spin rounded-full border-[3px] border-slate-300 border-t-blue-500 dark:border-slate-600 dark:border-t-blue-400" aria-hidden="true"></span>
        {{ t("live.sidebar.transcribing") }}
      </div>
      <div v-if="resultText" class="mt-2 rounded-xl bg-emerald-500/10 p-3 text-left text-sm text-emerald-900 dark:text-emerald-100" role="status">
        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-700 dark:text-emerald-400">{{ t("live.sidebar.fullText") }}</p>
        {{ resultText }}
      </div>
      <div v-if="resultKeywords.length" class="mt-2 flex flex-wrap gap-1.5">
        <span
          v-for="(keyword, index) in resultKeywords"
          :key="`${keyword}-${index}`"
          class="rounded-full bg-slate-900/5 px-2.5 py-0.5 text-xs font-medium text-slate-600 dark:bg-white/10 dark:text-slate-300"
        >
          {{ keyword }}
        </span>
      </div>
      <div v-if="isEmptyWarning" class="mt-2 rounded-xl bg-yellow-500/10 p-2 text-sm text-yellow-800 dark:bg-yellow-500/15 dark:text-yellow-200" role="status">
        {{ t("live.sidebar.emptyTranscript") }}
      </div>
      <div v-if="apiError" class="mt-2 rounded-xl bg-red-500/10 p-2 text-sm text-red-700 dark:bg-red-500/15 dark:text-red-200" role="alert">{{ apiError }}</div>
    </details>

    <!-- History -->
    <section :aria-label="t('live.sidebar.historyLabel')" class="pb-2">
      <slot name="history" />
    </section>
  </aside>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { TranscriptItem } from "../types";

const { t } = useI18n({ useScope: "global" });

// Sidebar: visual relocation only, no transcription or slide logic here.
// Branding and theme live in the persistent navbar; only the status stays.
defineProps<{
  statusLabel: string;
  statusPillClass: string;
  liveActive: boolean;
  clearDisabled: boolean;
  presentationTopic: string;
  presentationAudience: string;
  notice: string | null;
  error: string | null;
  prefilterEnabled: boolean;
  prefilterThreshold: number;
  prefilterLevel: number;
  partialText: string;
  serverPaused: boolean;
  finalItems: TranscriptItem[];
  lastFiltered: boolean;
  canTranscribe: boolean;
  batchLoading: boolean;
  resultText: string;
  resultKeywords: string[];
  isEmptyWarning: boolean;
  apiError: string | null;
}>();

const emit = defineEmits<{
  (e: "start-live"): void;
  (e: "stop-live"): void;
  (e: "clear-live"): void;
  (e: "update:topic", value: string): void;
  (e: "update:audience", value: string): void;
  (e: "prefilter-enabled", value: boolean): void;
  (e: "prefilter-threshold", value: number): void;
  (e: "batch-transcribe"): void;
}>();
</script>
