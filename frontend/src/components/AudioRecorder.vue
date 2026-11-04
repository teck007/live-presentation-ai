<template>
  <section class="flex flex-col gap-3">
    <div class="flex justify-center gap-2">
      <button
        v-if="!isRecording"
        type="button"
        class="rounded-lg px-5 py-2.5 transition bg-red-700 text-white hover:bg-red-800"
        @click="emit('start')"
      >
        {{ t("live.recorder.record") }}
      </button>
      <button
        v-else
        type="button"
        class="rounded-lg px-5 py-2.5 transition bg-slate-500 text-white hover:bg-slate-600"
        @click="emit('stop')"
      >
        {{ t("live.recorder.stop", { s: elapsed }) }}
      </button>
      <button
        v-if="audioUrl && !isRecording"
        type="button"
        class="rounded-lg px-5 py-2.5 transition border border-slate-300 bg-transparent text-slate-700 hover:bg-slate-500/10 dark:border-white/10 dark:text-slate-200 dark:hover:bg-white/10"
        @click="emit('clear')"
      >
        {{ t("live.recorder.clear") }}
      </button>
    </div>

    <p v-if="isRecording" class="font-bold text-red-600 animate-pulse dark:text-red-400" role="status">
      {{ t("live.recorder.recording", { s: elapsed }) }}
    </p>
    <audio
      v-if="audioUrl && !isRecording"
      :src="audioUrl"
      controls
      class="w-full"
    />
    <p v-if="recorderError" class="rounded-md bg-red-500/10 p-2 text-red-700 dark:bg-red-500/15 dark:text-red-300" role="alert">
      {{ recorderError }}
    </p>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";

// Recorder view: only presents state and emits events.
// MediaRecorder logic lives in the useRecorder composable.
const { t } = useI18n({ useScope: "global" });

defineProps<{
  isRecording: boolean;
  audioUrl: string | null;
  elapsed: number;
  recorderError: string | null;
}>();

const emit = defineEmits<{
  (e: "start"): void;
  (e: "stop"): void;
  (e: "clear"): void;
}>();
</script>
