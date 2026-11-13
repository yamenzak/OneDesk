<template>
  <div class="flex flex-col gap-4">
    <FormControl v-model="answers.owner.first_name" size="lg" :label="__('First Name')" autocomplete="given-name" required />
    <FormControl v-model="answers.owner.last_name" size="lg" :label="__('Last Name')" autocomplete="family-name" />
    <FormControl
      v-if="!offer.me"
      v-model="email"
      size="lg"
      type="email"
      :label="__('Email')"
      autocomplete="email"
      required
      :description="about"
    />
    <p v-else class="text-p-base text-ink-gray-6">{{ __("Signed in as {0}. The workspace joins your account.", [offer.me]) }}</p>
    <p v-if="!offer.me" class="text-p-sm text-ink-gray-6">
      {{ __("Have a One account?") }}
      <a class="font-medium text-ink-gray-8 underline" href="/login?redirect-to=/start#login-with-email-link">{{ __("Sign In") }}</a>
    </p>
  </div>
</template>

<script setup>
import { computed } from "vue";
import { FormControl } from "frappe-ui";

import { __ } from "../words";
import { answers, email, offer } from "./wizard";

const about = __("Your One account, the workspace's first administrator, and where the receipt goes.");
const ready = computed(() => Boolean(answers.owner.first_name.trim() && (offer.value.me || /^\S+@\S+\.\S+$/.test(email.value.trim()))));

defineExpose({ ready, said: () => ({}) });
</script>
