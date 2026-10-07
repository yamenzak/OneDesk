<template>
  <!-- What happened on the record, frappe's own timeline, newest first as a
       form's Activity is, with a comment written at its top and New Email
       opening frappe's Email dialog (kit ActivityComposer); an email is
       answered from its own row with Reply or Reply All. -->
  <div class="flex flex-col gap-4 pb-10 pt-2">
    <ActivityComposer ref="composer" :doctype="doctype" :name="name" @sent="reload?.()" />
    <ActivityTimeline :activities="newest" :loading="loading">
      <template #item-email="{ activity: one }">
        <EmailItem :email="one">
          <template #actions>
            <Button variant="ghost" size="sm" icon="lucide-reply" :tooltip="__('Reply')" :aria-label="__('Reply')" @click="composer?.reply(one)" />
            <Button variant="ghost" size="sm" icon="lucide-reply-all" :tooltip="__('Reply All')" :aria-label="__('Reply All')" @click="composer?.reply(one, true)" />
          </template>
        </EmailItem>
      </template>
    </ActivityTimeline>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";
import { ActivityTimeline, EmailItem, useActivityTimeline } from "@framework/ui/ActivityTimeline";

import { ActivityComposer, __ } from "../kit";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
});
const { activities, loading, reload } = useActivityTimeline(props.doctype, props.name);
const newest = computed(() => [...(activities.value || [])].reverse());
const composer = ref(null);
</script>
