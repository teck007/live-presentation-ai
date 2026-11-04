<!-- DEPRECATED: kept for backwards compatibility only. The persistent
  AppNavbar (mounted in App.vue) is the single navbar now; LandingView no
  longer uses this component. It delegates here to avoid duplication. -->
<template>
  <AppNavbar />
</template>

<script setup lang="ts">
import AppNavbar from "../AppNavbar.vue";
</script>
