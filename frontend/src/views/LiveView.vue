<template>
  <div class="flex h-full min-h-0 flex-1 bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
    <a
      href="#lienzo"
      class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-emerald-600 focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-white"
    >
      {{ t("live.skipToCanvas") }}
    </a>
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
    <div v-if="sidebarOpen" id="mobile-sidebar" class="fixed inset-0 z-40 md:hidden" @keydown.escape="sidebarOpen = false">
      <div class="absolute inset-0 bg-black/60" @click="sidebarOpen = false"></div>
      <div role="dialog" aria-modal="true" :aria-label="t('live.controlsLabel')" class="absolute inset-y-0 left-0">
        <button
          type="button"
          :aria-label="t('live.closeMenu')"
          class="absolute right-3 top-3 z-10 rounded-xl border border-slate-300 bg-white p-2 text-slate-700 dark:border-white/10 dark:bg-slate-800 dark:text-slate-200"
          @click="sidebarOpen = false"
        >
          <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M5.3 5.3a1 1 0 0 1 1.4 0L10 8.6l3.3-3.3a1 1 0 1 1 1.4 1.4L11.4 10l3.3 3.3a1 1 0 0 1-1.4 1.4L10 11.4l-3.3 3.3a1 1 0 0 1-1.4-1.4L8.6 10 5.3 6.7a1 1 0 0 1 0-1.4Z"/></svg>
        </button>
        <AppSidebar
          class="flex rounded-r-3xl"
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
          @start-live="handleStartLiveAndClose"
          @stop-live="handleStopLiveAndClose"
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
    </div>

    <!-- Stage -->
    <main class="flex-1 overflow-y-auto bg-gradient-to-br from-slate-100 via-white to-slate-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <!-- Resume dialog: saved live session found, BEFORE mic activation -->
      <div
        v-if="resumeOffer"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
        role="dialog"
        aria-modal="true"
        :aria-label="t('live.resume.title')"
        @keydown.escape="cancelResume"
      >
        <div class="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl dark:bg-slate-900">
          <h2 class="text-lg font-bold text-slate-900 dark:text-white">{{ t("live.resume.title") }}</h2>
          <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
            {{ t("live.resume.found", { n: resumeOffer.slide_count }) }}
          </p>
          <dl class="mt-3 space-y-1 text-sm text-slate-500 dark:text-slate-400">
            <div v-if="resumeOffer.topic" class="flex gap-2">
              <dt class="font-medium">{{ t("live.resume.topic") }}</dt>
              <dd class="truncate">{{ resumeOffer.topic }}</dd>
            </div>
            <div v-if="resumeUpdatedAt" class="flex gap-2">
              <dt class="font-medium">{{ t("live.resume.updated") }}</dt>
              <dd>{{ resumeUpdatedAt }}</dd>
            </div>
          </dl>
          <div class="mt-5 flex flex-wrap justify-end gap-2">
            <button
              type="button"
              class="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
              @click="cancelResume"
            >
              {{ t("live.resume.cancel") }}
            </button>
            <button
              type="button"
              :disabled="resumeBusy"
              class="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
              @click="startFreshFromResume"
            >
              {{ t("live.resume.fresh") }}
            </button>
            <button
              type="button"
              :disabled="resumeBusy"
              class="rounded-2xl bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
              @click="continueResume"
            >
              {{ t("live.resume.continue") }}
            </button>
          </div>
        </div>
      </div>

      <!-- Mobile top bar (brand/theme live in the persistent navbar) -->
      <div class="sticky top-0 z-30 flex items-center gap-3 border-b border-slate-200 bg-white/80 p-3 backdrop-blur md:hidden dark:border-white/10 dark:bg-slate-950/80">
        <button
          type="button"
          :aria-label="t('live.openMenu')"
          :aria-expanded="sidebarOpen"
          aria-controls="mobile-sidebar"
          class="rounded-xl border border-slate-300 bg-slate-500/5 p-2 text-slate-700 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
          @click="sidebarOpen = true"
        >
          <svg class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M3 5h14v2H3zM3 9h14v2H3zM3 13h14v2H3z"/></svg>
        </button>
        <span class="ml-auto rounded-full px-3 py-1 text-xs font-medium" :class="statusPillClass" role="status">
          {{ statusLabel }}
        </span>
      </div>

      <div class="mx-auto max-w-6xl px-4 py-6 md:px-8 md:py-10">
        <header class="text-center">
          <h1 class="text-2xl font-bold tracking-tight md:text-3xl">{{ t("live.title") }}</h1>
          <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
            {{ t("live.subtitle") }}
          </p>
        </header>

        <div class="mt-6">
          <SlideCanvas
            :slides="presentation.slides.value"
            :pending="presentation.pending.value > 0"
            :error="presentation.error.value"
            :last-filtered="!!presentation.lastFiltered.value"
            :scale="slideScale"
            @update:scale="setSlideScale"
            @retry="handleRetry"
          />
        </div>

        <!-- Subtitle bar below stage -->
        <div
          v-if="live.partialText.value"
          class="mx-auto mt-4 w-full max-w-5xl rounded-2xl border-l-4 border-blue-400 bg-blue-500/10 p-4 text-left italic text-slate-700 dark:bg-blue-500/15 dark:text-slate-300"
          role="status"
        >
          {{ live.partialText.value }}<span class="animate-pulse">…</span>
        </div>
        <div
          v-else-if="lastTurnKeywords.length"
          class="mx-auto mt-4 flex w-full max-w-5xl flex-wrap items-center gap-2"
        >
          <span class="text-xs uppercase tracking-widest text-slate-500">{{ t("live.lastTurn") }}</span>
          <span
            v-for="(keyword, kindex) in lastTurnKeywords"
            :key="`${keyword}-${kindex}`"
            class="rounded-full bg-slate-900/5 px-3 py-1 text-xs font-medium text-slate-600 dark:bg-white/10 dark:text-slate-300"
          >
            {{ keyword }}
          </span>
        </div>

        <details
          v-if="isDev"
          class="mx-auto mt-4 w-full max-w-5xl rounded-2xl border border-slate-200 bg-slate-500/5 p-4 dark:border-white/10 dark:bg-white/5"
        >
          <summary class="cursor-pointer text-sm font-semibold text-slate-800 dark:text-slate-200">
            {{ t("live.testTitle") }}
          </summary>
          <textarea
            v-model="testText"
            rows="3"
            :placeholder="t('live.testPlaceholder')"
            class="mt-3 w-full rounded-2xl border border-slate-300 bg-white p-3 text-sm text-slate-900 placeholder:text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:placeholder:text-slate-500"
          ></textarea>
          <div class="mt-3 flex items-center gap-3">
            <button
              type="button"
              :disabled="testText.trim().length < 3 || presentation.pending.value > 0"
              class="rounded-2xl border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200"
              @click="presentation.submitTestTranscript(testText)"
            >
              {{ t("live.testButton") }}
            </button>
            <span v-if="presentation.pending.value > 0" class="text-xs text-slate-500 dark:text-slate-400" role="status">
              {{ t("live.generating") }}
            </span>
          </div>
        </details>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import AppSidebar from "../components/AppSidebar.vue";
import AudioRecorder from "../components/AudioRecorder.vue";
import SlideCanvas from "../components/SlideCanvas.vue";
import TranscriptHistory from "../components/TranscriptHistory.vue";
import { transcribeAudio } from "../api/transcribe";
import {
  AuthRequiredError,
  TrialExpiredError,
  fetchTrialStatus,
} from "../api/auth";
import {
  discardLiveSession,
  fetchLiveSessionSlides,
  fetchLiveSessionStatus,
} from "../api/presentation";
import type { LiveSessionStatus } from "../types";
import { useLivePresentation } from "../composables/useLivePresentation";
import { useLanguage } from "../composables/useLanguage";
import { useRecorder } from "../composables/useRecorder";
import { useRealtimeTranscription } from "../composables/useRealtimeTranscription";
import { getAuth } from "../lib/clerk";
import type { TranscriptItem } from "../types";

// Live transcription session (realtime WS).

const router = useRouter();
const auth = getAuth();
const isDev = import.meta.env.DEV;
const { t } = useI18n({ useScope: "global" });

// Fresh Clerk JWT per request (null when signed out or dev without Clerk).
async function getToken(): Promise<string | null> {
  try {
    return (await auth?.getToken.value()) ?? null;
  } catch {
    return null;
  }
}

function goTrialExpired(): void {
  void router.replace({ name: "trial-expired" });
}

function goSignIn(): void {
  void router.replace({ name: "sign-in", query: { redirect: "/live" } });
}

// MVP presentation: topic + final-turn queue -> JSON slides.
const presentationTopic = ref("");
const presentationAudience = ref("general");
const { locale } = useLanguage();
const presentation = useLivePresentation({
  getToken,
  onTrialExpired: goTrialExpired,
  onUnauthorized: goSignIn,
});
presentation.setLanguage(locale.value);

// Dev-only test box: generates slides without speaking.
const testText = ref("");

// slide_* WS events render directly; the rest feeds transcription.
// live_session adopts the bridge id so retries reuse it (no dialog).
const live = useRealtimeTranscription({
  onSlideEvent: (event) => presentation.handleSlideEvent(event),
  onLiveSession: (id) => presentation.setLiveSessionId(id),
});

// Mobile drawer state (visual only).
const sidebarOpen = ref(false);

function handleEscape(e: KeyboardEvent) {
  if (e.key === "Escape") sidebarOpen.value = false;
}

onMounted(() => window.addEventListener("keydown", handleEscape));
onBeforeUnmount(() => {
  window.removeEventListener("keydown", handleEscape);
  if (scaleSyncTimer) clearTimeout(scaleSyncTimer);
});

watch(presentationTopic, (v) => {
  presentation.setTopic(v);
  live.sendSessionConfig({
    topic: v,
    audience: presentationAudience.value,
    language: locale.value,
    topicVersion: topicVersion.value,
    ...(presentation.paletteId.value ? { palette_id: presentation.paletteId.value } : {}),
  });
});

watch(presentationAudience, (v) => {
  presentation.setAudience(v);
  live.sendSessionConfig({
    topic: presentationTopic.value,
    audience: v,
    language: locale.value,
    topicVersion: topicVersion.value,
    ...(presentation.paletteId.value ? { palette_id: presentation.paletteId.value } : {}),
  });
});

// UI locale drives slide language from the next slide forward.
// No re-translation of already-painted slides; ASR bias re-handshakes
// upstream (backend) so the new bias takes effect mid-session.
watch(locale, (v) => {
  presentation.setLanguage(v);
  live.sendSessionConfig({
    topic: presentationTopic.value,
    audience: presentationAudience.value,
    language: v,
    topicVersion: topicVersion.value,
    ...(presentation.paletteId.value ? { palette_id: presentation.paletteId.value } : {}),
  });
});

// User text scale for the stage (80-130%, step 10): localStorage preference,
// adopted from the stored session on Continuar, synced to the backend via the
// config frame. Never touches slides/activeIndex: no jump, no reorder.
const SLIDE_SCALE_KEY = "live.slidescale";
const SLIDE_SCALE_MIN = 80;
const SLIDE_SCALE_MAX = 130;
const SLIDE_SCALE_STEP = 10;
const SLIDE_SCALE_DEFAULT = 100;

function snapSlideScale(value: unknown): number {
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return SLIDE_SCALE_DEFAULT;
  const clamped = Math.min(SLIDE_SCALE_MAX, Math.max(SLIDE_SCALE_MIN, n));
  return Math.round(clamped / SLIDE_SCALE_STEP) * SLIDE_SCALE_STEP;
}

function readSlideScale(): number {
  try {
    const raw = localStorage.getItem(SLIDE_SCALE_KEY);
    if (raw === null) return SLIDE_SCALE_DEFAULT;
    return snapSlideScale(Number(raw));
  } catch {
    return SLIDE_SCALE_DEFAULT;
  }
}

const slideScale = ref(readSlideScale());

function setSlideScale(value: number): void {
  slideScale.value = snapSlideScale(value);
}

// Current topic version: backend is authoritative; frontend mirrors it
// for the pre-paint guard and sends it in the `config` frame.
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
    // Flag-on: WS is the single producer; final turns skip the POST.
    // Flag-off: 4s debounce -> POST /api/presentations/generate (FIFO-1).
    // Count is consumed in both modes to avoid re-queue on flag flip.
    const fresh = items.slice(0, items.length - seenFinalCount);
    seenFinalCount = items.length;
    if (presentation.wsSlidesEnabled.value) return;
    // finalItems uses unshift: newest items come first.
    for (let i = fresh.length - 1; i >= 0; i--) {
      presentation.queueTranscript(fresh[i]);
    }
  },
);

async function handleStartLive() {
  // Reconnect within the same live: reuse the id, never show the dialog.
  if (
    live.status.value === "connecting" ||
    live.status.value === "listening" ||
    live.status.value === "speaking" ||
    live.status.value === "paused"
  ) {
    return;
  }
  presentation.setTopic(presentationTopic.value);
  presentation.setAudience(presentationAudience.value);
  presentation.setLanguage(locale.value);
  presentation.setTopicVersion(topicVersion.value);
  // Resume check BEFORE mic: saved session -> dialog; none/error -> direct.
  try {
    const status = await fetchLiveSessionStatus(getToken);
    if (status.has_saved && status.slide_count > 0 && status.live_session_id) {
      resumeOffer.value = status;
      return;
    }
  } catch {
    // Fail-open (dev sin auth): arranca directo.
  }
  await doStartLive(false);
}

/** Common start: mic + WS with the live session identity. */
async function doStartLive(resume: boolean) {
  presentation.setTopic(presentationTopic.value);
  presentation.setAudience(presentationAudience.value);
  presentation.setLanguage(locale.value);
  presentation.setTopicVersion(topicVersion.value);
  // Portada automática: arranque fresco + tema + canvas vacío. No bloquea el
  // mic (seq 0 queda primera aunque el WS pinte después). Continuar no genera.
  if (!resume && presentationTopic.value.trim().length >= 3 && presentation.slides.value.length === 0) {
    void presentation.generateCover(presentationTopic.value);
  }
  await live.start(await getToken());
  // Queued until WS OPEN (RealtimeClient + composable flush on onopen): no race if socket still connecting.
  live.sendSessionConfig({
    topic: presentationTopic.value,
    audience: presentationAudience.value,
    language: locale.value,
    topicVersion: topicVersion.value,
    ...(presentation.paletteId.value ? { palette_id: presentation.paletteId.value } : {}),
    liveSessionId: presentation.getLiveSessionId(),
    resume,
    displayScale: slideScale.value / 100,
  });
}

// Saved-session offer (Continuar / Nueva / Cancelar).
const resumeOffer = ref<LiveSessionStatus | null>(null);
const resumeBusy = ref(false);

const resumeUpdatedAt = computed(() => {
  const raw = resumeOffer.value?.updated_at;
  if (!raw) return "";
  const d = new Date(raw);
  return Number.isNaN(d.getTime()) ? raw : d.toLocaleString();
});

function cancelResume() {
  if (resumeBusy.value) return;
  resumeOffer.value = null;
}

/** Continuar: visual restore first (snapshot -> canvas), then WS with resume:true.
 * Topic/audience/palette come from the saved session; the bridge restores
 * seq/context live-side. 404/empty snapshot -> start empty, WS still resumes. */
async function continueResume() {
  const offer = resumeOffer.value;
  if (!offer?.live_session_id || resumeBusy.value) return;
  resumeBusy.value = true;
  try {
    presentation.setLiveSessionId(offer.live_session_id);
    if (offer.topic) {
      presentationTopic.value = offer.topic;
      presentation.setTopic(offer.topic);
    }
    try {
      const snapshot = await fetchLiveSessionSlides(offer.live_session_id, getToken);
      // Stored scale wins over the local default, then persists to localStorage.
      if (Number.isFinite(snapshot.displayScale)) {
        setSlideScale(Math.round(snapshot.displayScale * 100));
      }
      if (snapshot.topic) {
        presentationTopic.value = snapshot.topic;
        presentation.setTopic(snapshot.topic);
      }
      if (snapshot.slides.length > 0) {
        // Paint BEFORE starting the WS so the canvas shows history instantly.
        presentation.loadSnapshot(snapshot.slides);
        const first = snapshot.slides[0];
        if (first?.audience) {
          presentationAudience.value = first.audience;
          presentation.setAudience(first.audience);
        }
        const firstLang = (first as { language?: unknown }).language;
        if (firstLang === "es" || firstLang === "en") {
          presentation.setLanguage(firstLang);
        }
        if (typeof first?.palette_id === "string" && first.palette_id) {
          presentation.setPaletteId(first.palette_id);
        }
        if (snapshot.maxTopicVersion > 0) {
          topicVersion.value = snapshot.maxTopicVersion;
          presentation.setTopicVersion(snapshot.maxTopicVersion);
        }
      } else {
        console.info(`[resume] empty snapshot for ${offer.live_session_id}, starting empty`);
      }
    } catch (err) {
      // Fail-open: expired/deleted session paints nothing, WS still resumes.
      console.info(
        `[resume] snapshot unavailable, starting empty: ${err instanceof Error ? err.message : err}`,
      );
    }
    resumeOffer.value = null;
    await doStartLive(true);
  } finally {
    resumeBusy.value = false;
  }
}

/** Nueva: discard the saved session, fresh id, resume:false. */
async function startFreshFromResume() {
  const offer = resumeOffer.value;
  if (resumeBusy.value) return;
  resumeBusy.value = true;
  try {
    if (offer?.live_session_id) {
      try {
        await discardLiveSession(offer.live_session_id, getToken);
      } catch {
        // Fail-open: igual se arranca limpio.
      }
    }
    live.clearLive();
    seenFinalCount = 0;
    presentation.clear();
    presentation.rotateLiveSessionId();
    resumeOffer.value = null;
    await doStartLive(false);
  } finally {
    resumeBusy.value = false;
  }
}

async function handleStartLiveAndClose() {
  sidebarOpen.value = false;
  await handleStartLive();
}

function handleStopLive() {
  live.stop();
}

function handleStopLiveAndClose() {
  sidebarOpen.value = false;
  handleStopLive();
}

function handleClearLive() {
  live.clearLive();
  seenFinalCount = 0;
  presentation.clear();
}

/** Reintento: reencola el último transcript (POST) o reenvía el último turno (WS). */
function handleRetry() {
  const last = live.finalItems.value[0];
  if (last && last.text.trim().length >= 3) {
    void presentation.submitTestTranscript(last.text);
  } else {
    presentation.retryLast();
  }
}

const liveActive = computed(
  () =>
    live.status.value === "connecting" ||
    live.status.value === "listening" ||
    live.status.value === "speaking" ||
    live.status.value === "paused",
);

// Persist the scale preference; sync to the backend with a light debounce
// (no spam per click) and only while the WS is up. Nueva inherits the
// localStorage value because this is the only writer.
let scaleSyncTimer: ReturnType<typeof setTimeout> | null = null;
watch(slideScale, (v) => {
  try {
    localStorage.setItem(SLIDE_SCALE_KEY, String(v));
  } catch {
    // Persistencia opcional.
  }
  if (scaleSyncTimer) clearTimeout(scaleSyncTimer);
  scaleSyncTimer = setTimeout(() => {
    scaleSyncTimer = null;
    if (!liveActive.value) return;
    live.sendSessionConfig({ displayScale: v / 100 });
  }, 400);
});

const statusLabel = computed(() => {
  switch (live.status.value) {
    case "connecting":
      return t("live.status.connecting");
    case "listening":
      return t("live.status.listening");
    case "speaking":
      return t("live.status.speaking");
    case "paused":
      return t("live.status.paused");
    case "error":
      return t("live.status.error");
    default:
      return t("live.status.idle");
  }
});

const statusPillClass = computed(() => {
  switch (live.status.value) {
    case "listening":
      return "bg-blue-500/10 text-blue-800 dark:bg-blue-500/15 dark:text-blue-200";
    case "speaking":
      return "bg-emerald-500/10 text-emerald-800 dark:bg-emerald-500/15 dark:text-emerald-200";
    case "paused":
      return "bg-amber-500/10 text-amber-800 dark:bg-amber-500/15 dark:text-amber-200";
    case "connecting":
      return "bg-slate-500/10 text-slate-700 dark:bg-white/10 dark:text-slate-300";
    case "error":
      return "bg-red-500/10 text-red-700 dark:bg-red-500/15 dark:text-red-200";
    default:
      return "bg-slate-500/10 text-slate-500 dark:bg-white/10 dark:text-slate-400";
  }
});

// Last final turn keywords for the subtitle bar.
const lastTurnKeywords = computed(() => live.finalItems.value[0]?.keywords ?? []);

// Batch-recording state from the composable (fallback).
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

// Transcription and history state (most recent first).
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

/** Sends the recorded audio to the backend and updates history. */
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
    const data = await transcribeAudio(blob.value, filename, getToken, locale.value);
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
    if (error instanceof TrialExpiredError) {
      goTrialExpired();
      return;
    }
    if (error instanceof AuthRequiredError) {
      goSignIn();
      return;
    }
    apiError.value =
      error instanceof Error ? error.message : t("errors.unknown");
  } finally {
    loading.value = false;
  }
}

// WS rejected with 4401 (invalid session or ended trial): stop audio,
// re-check the trial once, then route (never loops: target has no guard).
watch(
  () => live.authBlocked.value,
  async (blocked) => {
    if (!blocked) return;
    live.stop();
    try {
      const status = await fetchTrialStatus(getToken);
      if (status.active) goSignIn();
      else goTrialExpired();
    } catch (error) {
      if (error instanceof AuthRequiredError) goSignIn();
      else goTrialExpired();
    }
  },
);
</script>
