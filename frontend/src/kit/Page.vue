<template>
  <div class="mx-auto w-full max-w-6xl px-5 pb-16 text-ink-gray-8" :class="{ 'lg:max-w-[85rem]': wide }">
    <slot />
  </div>
</template>

<script setup>
defineProps({ wide: Boolean });
</script>
