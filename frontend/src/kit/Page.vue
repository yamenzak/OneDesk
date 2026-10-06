<template>
  <!-- A screen's body: the width and the margins every island page shares.
       `wide` adds room for a column of its own beside it on a desktop, as a
       project's views are, keeping the body as wide as any other page's. -->
  <div class="mx-auto w-full max-w-6xl px-5 pb-16 text-ink-gray-8" :class="{ 'lg:max-w-[85rem]': wide }">
    <slot />
  </div>
</template>

<script setup>
defineProps({ wide: Boolean });
</script>
