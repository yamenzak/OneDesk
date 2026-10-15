<template>
  <!-- The reader's profile: frappe's own Edit Profile web form.
       Modelled on Shopify's customer account profile: one form, Save. -->
  <WebForm page="profile" :heading="__('Profile')" />
</template>

<script setup>
import WebForm from "../parts/WebForm.vue";
</script>
