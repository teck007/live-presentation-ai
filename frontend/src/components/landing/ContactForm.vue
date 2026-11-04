<template>
  <form
    class="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl dark:border-white/10 dark:bg-slate-900"
    :aria-label="t('contact.formLabel')"
    @submit.prevent="handleSubmit"
  >
    <h3 class="text-lg font-bold text-slate-900 dark:text-white">{{ t("contact.title") }}</h3>
    <p class="mt-1 text-sm text-slate-500 dark:text-slate-400">
      {{ t("contact.subtitle") }}
    </p>
    <div class="mt-4 grid gap-4">
      <div>
        <label for="contact-name" class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ t("contact.name") }}</label>
        <input
          id="contact-name"
          v-model="name"
          type="text"
          autocomplete="name"
          :placeholder="t('contact.namePlaceholder')"
          class="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-100 dark:placeholder:text-slate-500"
        />
        <p v-if="errors.name" class="mt-1 text-xs text-red-600 dark:text-red-400" role="alert">{{ errors.name }}</p>
      </div>
      <div>
        <label for="contact-email" class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ t("contact.email") }}</label>
        <input
          id="contact-email"
          v-model="email"
          type="email"
          autocomplete="email"
          :placeholder="t('contact.emailPlaceholder')"
          class="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-100 dark:placeholder:text-slate-500"
        />
        <p v-if="errors.email" class="mt-1 text-xs text-red-600 dark:text-red-400" role="alert">{{ errors.email }}</p>
      </div>
      <div>
        <label for="contact-message" class="text-sm font-medium text-slate-700 dark:text-slate-200">{{ t("contact.message") }}</label>
        <textarea
          id="contact-message"
          v-model="message"
          rows="4"
          :placeholder="t('contact.messagePlaceholder')"
          class="mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 dark:border-white/10 dark:bg-white/5 dark:text-slate-100 dark:placeholder:text-slate-500"
        ></textarea>
        <p v-if="errors.message" class="mt-1 text-xs text-red-600 dark:text-red-400" role="alert">{{ errors.message }}</p>
      </div>
    </div>
    <button
      type="submit"
      :disabled="pending"
      class="mt-4 w-full rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50 dark:bg-emerald-500 dark:text-slate-950 dark:hover:bg-emerald-400"
    >
      {{ pending ? t("contact.sending") : t("contact.send") }}
    </button>
    <p v-if="serverError" class="mt-3 text-sm text-red-600 dark:text-red-400" role="alert">
      {{ serverError }}
    </p>
    <p v-if="success" class="mt-3 text-sm text-emerald-700 dark:text-emerald-300" role="status">
      {{ t("contact.success") }}
    </p>
  </form>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { useI18n } from "vue-i18n";

const { t } = useI18n({ useScope: "global" });

const name = ref("");
const email = ref("");
const message = ref("");
const pending = ref(false);
const success = ref(false);
const serverError = ref<string | null>(null);
const errors = reactive({ name: "", email: "", message: "" });

function validate(): boolean {
  errors.name = name.value.trim().length >= 2 ? "" : t("contact.nameError");
  errors.email = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim())
    ? ""
    : t("contact.emailError");
  errors.message = message.value.trim().length >= 10 ? "" : t("contact.messageError");
  return !errors.name && !errors.email && !errors.message;
}

async function handleSubmit(): Promise<void> {
  success.value = false;
  serverError.value = null;
  if (!validate()) return;
  pending.value = true;
  try {
    const response = await fetch("/api/contact", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: name.value.trim(),
        email: email.value.trim(),
        message: message.value.trim(),
      }),
    });
    if (!response.ok) throw new Error(`Error ${response.status}`);
    success.value = true;
    name.value = "";
    email.value = "";
    message.value = "";
  } catch (error) {
    serverError.value =
      error instanceof Error
        ? t("contact.sendError", { msg: error.message })
        : t("contact.sendErrorGeneric");
  } finally {
    pending.value = false;
  }
}
</script>
