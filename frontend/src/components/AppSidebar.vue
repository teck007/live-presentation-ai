<template>
  <aside
    class="flex h-full w-[300px] shrink-0 flex-col gap-5 overflow-y-auto rounded-r-3xl border-r border-white/10 bg-slate-900/95 p-5 text-slate-200 backdrop-blur"
  >
    <!-- Logo / title -->
    <div class="flex items-center gap-3">
      <div class="flex size-10 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-blue-600 text-lg font-bold text-white" aria-hidden="true">
        LP
      </div>
      <div>
        <p class="text-base font-bold tracking-tight text-white">Live Presentation</p>
        <p class="text-xs text-slate-400">Transcripción en vivo</p>
      </div>
      <span class="ml-auto rounded-full px-3 py-1 text-xs font-medium" :class="statusPillClass" role="status">
        {{ statusLabel }}
      </span>
    </div>

    <!-- Live controls -->
    <section aria-label="Controles en vivo">
      <p class="text-xs font-semibold uppercase tracking-widest text-slate-400">En vivo</p>
      <div class="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:bg-emerald-900/50 disabled:text-slate-400"
          :disabled="liveActive"
          @click="emit('start-live')"
        >
          <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M7 4a3 3 0 0 1 6 0v6a3 3 0 0 1-6 0V4Z"/><path d="M4 10a6 6 0 0 0 12 0h-1.5a4.5 4.5 0 0 1-9 0H4Z"/><path d="M10 16.5v2.5h2v-2.5h-2Z"/></svg>
          Iniciar en vivo
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-xl bg-slate-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="!liveActive"
          @click="emit('stop-live')"
        >
          <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><rect x="5" y="5" width="10" height="10" rx="2"/></svg>
          Detener
        </button>
        <button
          type="button"
          class="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-400 transition hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
          :disabled="clearDisabled"
          @click="emit('clear-live')"
        >
          <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M6 4h8l1 2h3v2H2V6h3l1-2Zm-2 6h12l-1 6H5l-1-6Z"/></svg>
          Limpiar
        </button>
      </div>

      <div class="mt-3">
        <label class="block text-sm font-medium text-slate-300" for="presentation-topic">
          Tema principal de la presentación
        </label>
        <input
          id="presentation-topic"
          :value="presentationTopic"
          type="text"
          placeholder="Ej: cambio climático"
          class="mt-1 w-full rounded-xl border border-white/10 bg-slate-800 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
          @input="emit('update:topic', ($event.target as HTMLInputElement).value)"
        />
        <p class="mt-1 text-xs text-slate-500">
          Lo que no matchee este tema se descarta y no genera slide.
        </p>
      </div>

      <div class="mt-3">
        <label class="block text-sm font-medium text-slate-300" for="presentation-audience">
          Audiencia
        </label>
        <select
          id="presentation-audience"
          :value="presentationAudience"
          class="mt-1 w-full rounded-xl border border-white/10 bg-slate-800 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none"
          @change="emit('update:audience', ($event.target as HTMLSelectElement).value)"
        >
          <option value="ninos">Ninos</option>
          <option value="estudiantes">Estudiantes</option>
          <option value="general">General</option>
          <option value="profesionales">Profesionales</option>
          <option value="expertos">Expertos</option>
        </select>
        <p class="mt-1 text-xs text-slate-500">
          Ajusta el tono y la profundidad de cada slide.
        </p>
      </div>

      <div v-if="notice" class="mt-3 rounded-xl bg-blue-500/15 p-3 text-sm text-blue-200" role="status">
        {{ notice }}
      </div>
      <div v-if="error" class="mt-3 rounded-xl bg-red-500/15 p-3 text-sm text-red-200" role="alert">
        {{ error }}
        <span class="mt-1 block text-red-300">Puedes usar el grabador por lotes de abajo como alternativa.</span>
      </div>
    </section>

    <!-- Noise controls -->
    <section aria-label="Reducción de ruido" class="rounded-2xl border border-white/10 bg-slate-800/60 p-3">
      <p class="inline-flex items-center gap-2 text-sm font-medium text-slate-200">
        <svg class="size-4" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M4 6h12v2H4zM4 9h12v2H4zM4 12h7v2H4z"/></svg>
        Reducción de ruido
      </p>
      <label class="mt-2 flex cursor-pointer items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          class="size-4 accent-emerald-500"
          :checked="prefilterEnabled"
          @change="emit('prefilter-enabled', ($event.target as HTMLInputElement).checked)"
        />
        Activar filtro
      </label>
      <label class="mt-3 block text-sm text-slate-300">
        Cercanía
        <span class="block text-xs text-slate-500">Más a la derecha = solo muy cercano</span>
        <input
          type="range"
          min="0.01"
          max="0.05"
          step="0.005"
          class="mt-1 w-full accent-emerald-500"
          :value="prefilterThreshold"
          :disabled="!prefilterEnabled"
          @input="emit('prefilter-threshold', Number(($event.target as HTMLInputElement).value))"
        />
      </label>
      <div class="mt-2 flex items-center gap-2">
        <span class="text-xs text-slate-500">Nivel</span>
        <div class="h-2 flex-1 overflow-hidden rounded-full bg-slate-700" role="meter" aria-label="Nivel de micrófono">
          <div
            class="h-full rounded-full bg-emerald-500 transition-[width]"
            :style="{ width: `${Math.min(100, Math.round(prefilterLevel * 400))}%` }"
          ></div>
        </div>
      </div>
    </section>

    <!-- Live transcript summary -->
    <section aria-label="Transcripción en vivo">
      <p class="text-xs font-semibold uppercase tracking-widest text-slate-400">Transcripción</p>
      <div
        v-if="partialText"
        class="mt-2 rounded-xl border-l-4 border-blue-400 bg-slate-800 p-3 text-left text-sm italic text-slate-300"
        role="status"
        aria-live="polite"
      >
        {{ partialText }}<span class="animate-pulse">…</span>
      </div>
      <p v-else-if="liveActive" class="mt-2 text-sm text-slate-500">
        {{ serverPaused ? "En pausa por silencio prolongado. Habla para retomar." : "Escuchando… habla para transcribir." }}
      </p>
      <ul v-if="finalItems.length > 0" class="mt-2 max-h-48 space-y-2 overflow-y-auto text-left">
        <li
          v-for="(item, index) in finalItems"
          :key="`${item.sessionId ?? 'turn'}-${index}`"
          class="rounded-xl bg-emerald-500/10 p-3 text-sm text-emerald-100"
        >
          <p class="text-xs font-semibold uppercase tracking-wide text-emerald-400">Completo</p>
          {{ item.text }}
          <div v-if="item.keywords?.length" class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="(keyword, kindex) in item.keywords"
              :key="`${keyword}-${kindex}`"
              class="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-medium text-slate-300"
            >
              {{ keyword }}
            </span>
          </div>
        </li>
      </ul>
      <p v-if="lastFiltered" class="mt-2 text-xs text-slate-500">
        Último turno descartado por off-topic.
      </p>
    </section>

    <!-- Batch recorder -->
    <section aria-label="Grabador por lotes" class="rounded-2xl border border-white/10 bg-slate-800/60 p-3">
      <p class="text-sm font-semibold text-slate-200">Grabador por lotes</p>
      <p class="mt-1 text-xs text-slate-500">
        Alternativa: graba y presiona Transcribir.
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
        {{ batchLoading ? "Transcribiendo..." : "Transcribir" }}
      </button>
      <div v-if="batchLoading" class="mt-2 flex items-center justify-center gap-2 text-sm text-slate-300" role="status">
        <span class="inline-block size-[16px] animate-spin rounded-full border-[3px] border-slate-600 border-t-blue-400" aria-hidden="true"></span>
        Transcribiendo...
      </div>
      <div v-if="resultText" class="mt-2 rounded-xl bg-emerald-500/10 p-3 text-left text-sm text-emerald-100" role="status">
        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-400">Texto completo</p>
        {{ resultText }}
      </div>
      <div v-if="resultKeywords.length" class="mt-2 flex flex-wrap gap-1.5">
        <span
          v-for="(keyword, index) in resultKeywords"
          :key="`${keyword}-${index}`"
          class="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-medium text-slate-300"
        >
          {{ keyword }}
        </span>
      </div>
      <div v-if="isEmptyWarning" class="mt-2 rounded-xl bg-yellow-500/15 p-2 text-sm text-yellow-200" role="status">
        Transcripción vacía.
      </div>
      <div v-if="apiError" class="mt-2 rounded-xl bg-red-500/15 p-2 text-sm text-red-200" role="alert">{{ apiError }}</div>
    </section>

    <!-- History -->
    <section aria-label="Historial" class="pb-2">
      <slot name="history" />
    </section>
  </aside>
</template>

<script setup lang="ts">
import type { TranscriptItem } from "../types";

// Sidebar: visual relocation only, no transcription or slide logic here.
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
