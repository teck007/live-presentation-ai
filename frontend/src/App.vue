<template>
  <div class="flex h-screen bg-slate-950 text-white">
    <!-- Desktop sidebar -->
    <AppSidebar
      class="hidden md:flex"
      :status-label="statusLabel"
      :status-pill-class="statusPillClass"
      :live-active="liveActive"
      :clear-disabled="liveActive || (live.finalItems.value.length === 0 && !live.partialText.value)"
      :presentation-topic="presentationTopic"
      :presentation-audience="presentationAudience"
      :notice="live.notice.value"
      :error="live.error.value"
      :prefilter-enabled="live.prefilterEnabled.value"
      :prefilter-threshold="live.prefilterThreshold.value"
      :prefilter-level="live.prefilterLevel.value"
      :partial-text="live.partialText.value"
      :server-paused="live.serverPaused.value"
      :final-items="live.finalItems.value"
      :last-filtered="!!presentation.lastFiltered.value"
      :can-transcribe="canTranscribe"
      :batch-loading="loading"
      :result-text="resultText"
      :result-keywords="resultKeywords"
      :is-empty-warning="isEmptyWarning"
      :api-error="apiError"
      @start-live="handleStartLive"
      @stop-live="handleStopLive"
      @clear-live="handleClearLive"
      @update:topic="presentationTopic = $event; presentation.setTopic($event)"
      @update:audience="presentationAudience = $event; presentation.setAudience($event)"
      @prefilter-enabled="live.setPrefilterEnabled($event)"
      @prefilter-threshold="live.setPrefilterThreshold($event)"
      @batch-transcribe="handleTranscribe"
    >
      <template #recorder>
        <AudioRecorder
          :is-recording="isRecording"
          :audio-url="audioUrl"
          :elapsed="elapsed"
          :recorder-error="recorderError"
          @start="start"
          @stop="stop"
          @clear="handleClear"
        />
      </template>
      <template #history>
        <TranscriptHistory :items="history" />
      </template>
    </AppSidebar>

    <!-- Mobile sidebar drawer -->
    <div v-if="sidebarOpen" class="fixed inset-0 z-40 md:hidden">
      <div class="absolute inset-0 bg-black/60" @click="sidebarOpen = false"></div>
      <AppSidebar
        class="absolute inset-y-0 left-0 flex rounded-r-3xl"
        :status-label="statusLabel"
        :status-pill-class="statusPillClass"
        :live-active="liveActive"
        :clear-disabled="liveActive || (live.finalItems.value.length === 0 && !live.partialText.value)"
        :presentation-topic="presentationTopic"
        :presentation-audience="presentationAudience"
        :notice="live.notice.value"
        :error="live.error.value"
        :prefilter-enabled="live.prefilterEnabled.value"
        :prefilter-threshold="live.prefilterThreshold.value"
        :prefilter-level="live.prefilterLevel.value"
        :partial-text="live.partialText.value"
        :server-paused="live.serverPaused.value"
        :final-items="live.finalItems.value"
        :last-filtered="!!presentation.lastFiltered.value"
        :can-transcribe="canTranscribe"
        :batch-loading="loading"
        :result-text="resultText"
        :result-keywords="resultKeywords"
        :is-empty-warning="isEmptyWarning"
        :api-error="apiError"
      @start-live="handleStartLive"
      @stop-live="handleStopLive"
      @clear-live="handleClearLive"
      @update:topic="presentationTopic = $event; presentation.setTopic($event)"
      @update:audience="presentationAudience = $event; presentation.setAudience($event)"
      @prefilter-enabled="live.setPrefilterEnabled($event)"
      @prefilter-threshold="live.setPrefilterThreshold($event)"
      @batch-transcribe="handleTranscribe"
      >
        <template #recorder>
          <AudioRecorder
            :is-recording="isRecording"
            :audio-url="audioUrl"
            :elapsed="elapsed"
            :recorder-error="recorderError"
            @start="start"
            @stop="stop"
            @clear="handleClear"
          />
        </template>
        <template #history>
          <TranscriptHistory :items="history" />
        </template>
      </AppSidebar>
    </div>

    <!-- Stage -->
    <main class="flex-1 overflow-y-auto bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <!-- Mobile top bar -->
      <div class="sticky top-0 z-30 flex items-center gap-3 border-b border-white/10 bg-slate-950/80 p-3 backdrop-blur md:hidden">
        <button
          type="button"
          aria-label="Abrir menú"
          class="rounded-xl border border-white/10 bg-white/5 p-2 text-slate-200"
          @click="sidebarOpen = true"
        >
          <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M3 5h14v2H3zM3 9h14v2H3zM3 13h14v2H3z"/></svg>
        </button>
        <p class="text-sm font-semibold">Live Presentation</p>
        <span class="ml-auto rounded-full px-3 py-1 text-xs font-medium" :class="statusPillClass" role="status">
          {{ statusLabel }}
        </span>
      </div>

      <div class="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">
        <header class="text-center">
          <h1 class="text-2xl font-bold tracking-tight md:text-3xl">Presentación en vivo</h1>
          <p class="mt-1 text-sm text-slate-400">
            Habla y mira los slides generarse en tiempo real.
          </p>
        </header>

        <div class="mt-6">
          <SlideCanvas
            :slides="presentation.slides.value"
            :pending="presentation.pending.value > 0"
            :error="presentation.error.value"
          />
        </div>

        <!-- Subtitle bar below stage -->
        <div
          v-if="live.partialText.value"
          class="mx-auto mt-4 w-full max-w-5xl rounded-2xl border-l-4 border-blue-400 bg-white/5 p-4 text-left italic text-slate-300"
          role="status"
          aria-live="polite"
        >
          {{ live.partialText.value }}<span class="animate-pulse">…</span>
        </div>
        <div
          v-else-if="lastTurnKeywords.length"
          class="mx-auto mt-4 flex w-full max-w-5xl flex-wrap items-center gap-2"
          aria-live="polite"
        >
          <span class="text-xs uppercase tracking-widest text-slate-500">Último turno:</span>
          <span
            v-for="(keyword, kindex) in lastTurnKeywords"
            :key="`${keyword}-${kindex}`"
            class="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-slate-300"
          >
            {{ keyword }}
          </span>
        </div>

        <details
          open
          class="mx-auto mt-4 w-full max-w-5xl rounded-2xl border border-white/10 bg-white/5 p-4"
        >
          <summary class="cursor-pointer text-sm font-semibold text-slate-200">
            Probar transcripción (sin hablar)
          </summary>
          <textarea
            v-model="testText"
            rows="3"
            placeholder="Ej: tiene tres pasos: primero..."
            class="mt-3 w-full rounded-2xl border border-white/10 bg-white/5 p-3 text-sm text-slate-200 placeholder:text-slate-500"
          ></textarea>
          <div class="mt-3 flex items-center gap-3">
            <button
              type="button"
              :disabled="testText.trim().length < 3 || presentation.pending.value > 0"
              class="rounded-2xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 disabled:opacity-50"
              @click="presentation.submitTestTranscript(testText)"
            >
              Generar slide de prueba
            </button>
            <span v-if="presentation.pending.value > 0" class="text-xs text-slate-400">
              Generando…
            </span>
          </div>
          <p v-if="presentation.error.value" class="mt-2 text-sm text-red-400" role="alert">
            {{ presentation.error.value }}
          </p>
        </details>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import AppSidebar from "./components/AppSidebar.vue";
import AudioRecorder from "./components/AudioRecorder.vue";
import SlideCanvas from "./components/SlideCanvas.vue";
import TranscriptHistory from "./components/TranscriptHistory.vue";
import { transcribeAudio } from "./api/transcribe";
import { useLivePresentation } from "./composables/useLivePresentation";
import { useRecorder } from "./composables/useRecorder";
import { useRealtimeTranscription } from "./composables/useRealtimeTranscription";
import type { TranscriptItem } from "./types";

// Sesion de transcripcion en vivo (realtime WS).

// MVP presentación: topic + cola de turnos finales -> slides JSON.
const presentationTopic = ref("");
const presentationAudience = ref("general");
const presentation = useLivePresentation();

// Caja de prueba siempre visible: genera slides sin hablar.
const testText = ref("");

// Los eventos slide_* del WS pintan directo; el resto alimenta la transcripción.
const live = useRealtimeTranscription({
  onSlideEvent: (event) => presentation.handleSlideEvent(event),
});

// Mobile drawer state (visual only).
const sidebarOpen = ref(false);

watch(presentationTopic, (v) => {
  presentation.setTopic(v);
  live.sendSessionConfig({
    topic: v,
    audience: presentationAudience.value,
    topicVersion: topicVersion.value,
    ...(presentation.paletteId.value ? { palette_id: presentation.paletteId.value } : {}),
  });
});

watch(presentationAudience, (v) => {
  presentation.setAudience(v);
  live.sendSessionConfig({
    topic: presentationTopic.value,
    audience: v,
    topicVersion: topicVersion.value,
    ...(presentation.paletteId.value ? { palette_id: presentation.paletteId.value } : {}),
  });
});

// Versión de topic vigente: el backend es la autoridad; el frontend la refleja
// para el pre-paint guard y la envía en el frame `config`.
const topicVersion = ref(1);
watch(
  () => live.topicVersion.value,
  (v) => presentation.setTopicVersion(v),
);
watch(
  () => presentation.currentTopicVersion.value,
  (v) => {
    topicVersion.value = v;
  },
);

let seenFinalCount = 0;
watch(
  () => live.finalItems.value.length,
  () => {
    const items = live.finalItems.value;
    // Flag-on: el WS es el único productor; los turnos finales no van al POST.
    // Flag-off: debounce 4s -> POST /api/presentations/generate (FIFO-1).
    // Se consume el conteo en ambos modos para no reencolar al cambiar el flag.
    const fresh = items.slice(0, items.length - seenFinalCount);
    seenFinalCount = items.length;
    if (presentation.wsSlidesEnabled.value) return;
    // finalItems usa unshift: los nuevos están al inicio.
    for (let i = fresh.length - 1; i >= 0; i--) {
      presentation.queueTranscript(fresh[i]);
    }
  },
);

async function handleStartLive() {
  presentation.setTopic(presentationTopic.value);
  presentation.setAudience(presentationAudience.value);
  presentation.setTopicVersion(topicVersion.value);
  await live.start();
  // Queued until WS OPEN (RealtimeClient + composable flush on onopen): no race if socket still connecting.
  live.sendSessionConfig({
    topic: presentationTopic.value,
    audience: presentationAudience.value,
    topicVersion: topicVersion.value,
    ...(presentation.paletteId.value ? { palette_id: presentation.paletteId.value } : {}),
  });
}

function handleStopLive() {
  live.stop();
}

function handleClearLive() {
  live.clearLive();
  seenFinalCount = 0;
  presentation.clear();
}

const liveActive = computed(
  () =>
    live.status.value === "connecting" ||
    live.status.value === "listening" ||
    live.status.value === "speaking" ||
    live.status.value === "paused",
);

const statusLabel = computed(() => {
  switch (live.status.value) {
    case "connecting":
      return "Conectando…";
    case "listening":
      return "Escuchando";
    case "speaking":
      return "Hablando";
    case "paused":
      return "En pausa";
    case "error":
      return "Error";
    default:
      return "Inactivo";
  }
});

const statusPillClass = computed(() => {
  switch (live.status.value) {
    case "listening":
      return "bg-blue-100 text-blue-800";
    case "speaking":
      return "bg-green-100 text-green-800";
    case "paused":
      return "bg-yellow-100 text-yellow-800";
    case "connecting":
      return "bg-neutral-200 text-neutral-700";
    case "error":
      return "bg-red-100 text-red-700";
    default:
      return "bg-neutral-100 text-neutral-500";
  }
});

// Keywords del último turno final para la barra de subtítulos.
const lastTurnKeywords = computed(() => live.finalItems.value[0]?.keywords ?? []);

// Estado de grabacion por lotes provisto por el composable (fallback).
const {
  isRecording,
  blob,
  audioUrl,
  elapsed,
  error: recorderError,
  start,
  stop,
  clear,
  suggestedExtension,
} = useRecorder();

// Estado de la transcripcion y del historial (mas reciente primero).
const loading = ref(false);
const resultText = ref("");
const resultCleaned = ref("");
const resultTopic = ref("");
const resultKeywords = ref<string[]>([]);
const isEmptyWarning = ref(false);
const apiError = ref<string | null>(null);
const history = ref<TranscriptItem[]>([]);

const canTranscribe = computed(() => blob.value !== null && !loading.value);

function handleClear() {
  clear();
  resultText.value = "";
  resultCleaned.value = "";
  resultTopic.value = "";
  resultKeywords.value = [];
  isEmptyWarning.value = false;
  apiError.value = null;
}

/** Envia el audio grabado al backend y actualiza el historial. */
async function handleTranscribe() {
  if (!canTranscribe.value || !blob.value) return;
  loading.value = true;
  resultText.value = "";
  resultCleaned.value = "";
  resultTopic.value = "";
  resultKeywords.value = [];
  isEmptyWarning.value = false;
  apiError.value = null;
  try {
    const filename = `grabacion.${suggestedExtension()}`;
    const data = await transcribeAudio(blob.value, filename);
    const raw = data.text.trim();
    const cleaned = (data.cleaned ?? data.topic ?? "").trim();
    const topic = (data.topic ?? "").trim();
    const keywords = data.keywords ?? [];
    resultText.value = raw;
    resultCleaned.value = cleaned;
    resultTopic.value = topic;
    resultKeywords.value = keywords;
    history.value.unshift({ text: raw, cleaned, topic, keywords, sessionId: data.sessionId ?? null });
    if (raw) {
      resultText.value = raw;
    } else {
      isEmptyWarning.value = true;
    }
  } catch (error) {
    apiError.value =
      error instanceof Error ? error.message : "Error desconocido.";
  } finally {
    loading.value = false;
  }
}
</script>
