<template>
  <section v-if="items.length > 0" class="mt-6 text-left">
    <h3 class="text-lg font-semibold text-slate-900 dark:text-white">{{ t("live.history.title", { n: items.length }) }}</h3>
    <p class="rounded-md bg-blue-500/10 p-2.5 text-slate-700 dark:bg-blue-500/15 dark:text-blue-200">
      <strong>{{ t("live.history.latest") }}</strong> {{ items[0]?.text }}
    </p>
    <ol class="list-decimal space-y-2 pl-5 text-slate-700 dark:text-slate-300">
      <li v-for="(item, index) in items" :key="index">
        <p>{{ item.text }}</p>
        <div v-if="item.keywords?.length" class="mt-1 flex flex-wrap gap-1.5">
          <span
            v-for="(keyword, kIndex) in item.keywords"
            :key="`${keyword}-${kIndex}`"
            class="rounded-full bg-slate-500/10 px-2.5 py-0.5 text-xs font-medium text-slate-700 dark:bg-white/10 dark:text-slate-300"
          >
            {{ keyword }}
          </span>
        </div>
        <small v-if="item.sessionId" class="text-sm text-slate-400 dark:text-slate-500"
          >{{ t("live.history.sessionId", { id: item.sessionId }) }}</small
        >
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import type { TranscriptItem } from "../types";

const { t } = useI18n({ useScope: "global" });

// Shows the history with the most recent first.
defineProps<{
  items: TranscriptItem[];
}>();
</script>
