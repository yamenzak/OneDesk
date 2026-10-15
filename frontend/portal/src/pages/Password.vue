<template>
  <!-- A new password: frappe's own update_password (one/signin.py tells the
       person afterwards) and its strength test as it is typed.
       Modelled on GitHub's Change password: three fields and Update. -->
  <Head :title="__('Password')">
    <template #actions>
      <Button variant="solid" :label="__('Update')" :loading="saving" :disabled="!ready" @click="save" />
    </template>
  </Head>
  <div class="mx-auto w-full max-w-md px-4 py-6 sm:px-6">
    <form class="flex flex-col gap-4" @submit.prevent="save">
      <FormControl v-model="old" type="password" :label="__('Current Password')" autocomplete="current-password" required />
      <FormControl v-model="fresh" type="password" :label="__('New Password')" autocomplete="new-password" required :description="strength" />
      <FormControl v-model="again" type="password" :label="__('Confirm Password')" autocomplete="new-password" required :error="again && again !== fresh ? __('The two passwords are not the same.') : ''" />
      <FormControl v-model="everywhere" type="checkbox" :label="__('Sign out of every other device')" />
    </form>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { Button, FormControl, debounce, toast } from "frappe-ui";

import { call } from "../call";
import Head from "../parts/Head.vue";
import { __ } from "../words";

const old = ref("");
const fresh = ref("");
const again = ref("");
const everywhere = ref(false);
const saving = ref(false);
const strength = ref("");
const strong = ref(false);

const ready = computed(() => old.value && fresh.value && fresh.value === again.value && strong.value);

watch(
  fresh,
  debounce(async (value) => {
    if (!value) return (strength.value = "");
    const said = await call("frappe.core.doctype.user.user.test_password_strength", { new_password: value });
    strong.value = Boolean(said?.feedback?.password_policy_validation_passed);
    strength.value = said?.feedback?.warning || said?.feedback?.suggestions?.[0] || (strong.value ? __("Strong enough") : "");
  }, 300),
);

async function save() {
  if (!ready.value) return;
  saving.value = true;
  try {
    await call("frappe.core.doctype.user.user.update_password", {
      old_password: old.value,
      new_password: fresh.value,
      logout_all_sessions: everywhere.value ? 1 : 0,
    });
    old.value = fresh.value = again.value = "";
    toast.success(__("Password updated"));
  } catch (error) {
    toast.error(error?.messages?.[0] || __("Couldn't update the password."));
  } finally {
    saving.value = false;
  }
}
</script>
