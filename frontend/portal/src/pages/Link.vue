<template>
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

call("onedesk.one_portal.share.link_view", { token: props.token })
  .then((page) => (said.value = page))
  .catch((error) => (failed.value = error?.messages?.[0] || __("This link no longer works. Ask whoever sent it for a new one.")));
</script>
