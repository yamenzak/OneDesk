<template>
  <!-- What happened on the record, frappe's own timeline, with a comment or
       an email written at its foot (kit ActivityComposer), and an email
       answered from its own row with Reply. -->
  <div class="flex flex-col gap-4 pb-10 pt-2">
    <TimelineContainer>
      <ActivityTimeline :activities="activities" :loading="loading">
        <template #item-email="{ activity: one }">
          <EmailItem :email="one">
            <template #actions>
              <Button variant="ghost" size="sm" icon-left="lucide-reply" :label="__('Reply')" @click="composer?.reply(one)" />
            </template>
          </EmailItem>
        </template>
      </ActivityTimeline>
    </TimelineContainer>
    <ActivityComposer ref="composer" :doctype="doctype" :name="name" :title="title" @sent="reload?.()" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import { Button } from "frappe-ui";
import { ActivityTimeline, EmailItem, TimelineContainer, useActivityTimeline } from "@framework/ui/ActivityTimeline";

import { ActivityComposer, __ } from "../kit";

const props = defineProps({
  doctype: { type: String, required: true },
  name: { type: String, required: true },
  title: { type: String, default: "" },
});
const { activities, loading, reload } = useActivityTimeline(props.doctype, props.name);
const composer = ref(null);
</script>
