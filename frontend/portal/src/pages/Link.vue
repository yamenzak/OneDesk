<template>
  <!-- A record opened through a signed link (one/portal_share.py), by
       somebody without an account: the portal's own page for it, with who
       sent it and who it is for above, and nothing else to go to.
       Modelled on Stripe's hosted invoice page and DocuSign's signing page:
       one thing, from one sender, to one person. -->
  <div v-if="said" class="mx-auto w-full max-w-6xl px-4 pt-5 sm:px-6">
    <p class="text-sm text-ink-gray-6">{{ __("From {0}, for {1}", [said.workspace, said.party]) }}</p>
  </div>
  <Record v-if="said?.kind === 'record'" :token="token" :link="said" />
  <Rfq v-else-if="said?.kind === 'rfq'" :token="token" :link="said" />
  <Empty v-else-if="failed" :title="__('Link not working')" :line="failed" />
  <Loading v-else />
</template>

<script setup>
import { ref } from "vue";

import { call } from "../call";
import Empty from "../parts/Empty.vue";
import Loading from "../parts/Loading.vue";
import { __ } from "../words";
import Record from "./Record.vue";
import Rfq from "./Rfq.vue";

const props = defineProps({ token: { type: String, required: true } });
const said = ref(null);
const failed = ref("");

call("onedesk.one.portal_share.link_view", { token: props.token })
  .then((page) => (said.value = page))
  .catch((error) => (failed.value = error?.messages?.[0] || __("This link no longer works. Ask whoever sent it for a new one.")));
</script>
