<script setup lang="ts">
withDefaults(defineProps<{ size?: number; avatar?: boolean }>(), {
  size: 40,
  avatar: true,
});
</script>

<template>
  <v-avatar
    variant="text"
    :size="size"
    :class="{ 'rounded-circle': avatar, rounded: !avatar }"
  >
    <img :src="`/assets/isotipo.svg`" alt="Romm Logo" :width="size" />
  </v-avatar>
</template>

<style scoped>
.v-avatar {
  transition:
    filter 0.15s ease-in-out,
    border-radius 0.15s ease-in-out;
}
.v-avatar:hover,
.v-avatar.active {
  filter: drop-shadow(0px 0px 2px rgba(var(--v-theme-primary)));
}
</style>

