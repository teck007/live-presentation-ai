<template>
  <div class="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
    <AppNavbar />
    <div class="flex min-w-0 flex-1 flex-col">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppNavbar from "./components/AppNavbar.vue";

// App shell: persistent navbar on top, route content fills the rest.
// Theme + language init happen in main.ts before mount (anti-FOUC).
</script>
