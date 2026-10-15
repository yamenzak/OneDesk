<template>
  <!-- An address of the reader's, or a new one: erpnext's Addresses web form.
       Modelled on Shopify's customer account addresses: one form, Save. -->
  <WebForm
    page="addresses"
    :name="name === 'new' ? null : name"
    :heading="name === 'new' ? __('New Address') : ''"
    :crumbs="[{ label: tab, route: '/addresses' }]"
    after="/addresses"
  />
</template>

<script setup>
import { computed } from "vue";

import WebForm from "../parts/WebForm.vue";
import { __, boot } from "../words";

defineProps({ name: { type: String, required: true } });
const tab = computed(() => boot().tabs?.find((one) => one.path === "addresses")?.title || __("Addresses"));
</script>
