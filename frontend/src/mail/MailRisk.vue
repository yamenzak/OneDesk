<template>
  <OneAlert :colour="risk.held ? 'red' : 'yellow'" role="alert">
    <p class="font-medium text-ink-gray-9">{{ risk.held ? __("Held because it may be dangerous") : __("Be careful with this message") }}</p>
    <ul class="mt-1 list-disc space-y-0.5 ps-4 text-ink-gray-7">
      <li v-for="reason in risk.reasons" :key="reason" class="break-words">{{ reason }}</li>
    </ul>
    <p v-if="risk.held" class="mt-1 text-ink-gray-6">{{ __("No rule, reply or agent has seen it. Release it only if you trust the sender.") }}</p>
    <p v-if="links" class="mt-1 text-ink-gray-6">{{ risk.held ? __("Links in this message open only in Preview Link.") : __("Links in this message open Preview Link first.") }}</p>
    <div v-if="risk.held || links" class="mt-2 flex flex-wrap gap-2">
      <Button v-if="links" size="sm" variant="subtle" icon-left="lucide-scan-eye" :label="__('Preview Link')" @click="emit('preview')" />
      <template v-if="risk.held">
        <Button size="sm" variant="subtle" icon-left="lucide-inbox" :label="__('Release')" @click="emit('release')" />
        <Button size="sm" variant="subtle" theme="red" icon-left="lucide-trash-2" :label="__('Delete')" @click="emit('discard')" />
      </template>
    </div>
  </OneAlert>
</template>

<script setup>
// A message's warning (one_mail/held.py `said_of`): held, with Release and
// Delete under its reasons so they wrap on a phone, or only warned; Preview
// Link where it has links (one_mail/sandbox.py).
import { Button } from "frappe-ui";

import { OneAlert, __ } from "../kit";

defineProps({ risk: { type: Object, required: true }, links: { type: Number, default: 0 } });
const emit = defineEmits(["release", "discard", "preview"]);
</script>
