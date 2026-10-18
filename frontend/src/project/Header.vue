<template>
  <header class="pt-6">
    <div v-if="!said.media.length" class="relative rounded-7 bg-surface-gray-2 p-6 lg:p-8">
      <Button v-if="said.can_write" class="absolute end-4 top-4 lg:end-6 lg:top-6" variant="outline" icon-left="lucide-image-plus" :label="__('Add Cover')" @click="add" />
      <div class="mb-2 text-sm font-medium uppercase tracking-widest text-ink-gray-5">{{ __(said.kind) }}</div>
      <div class="flex items-end justify-between gap-6">
        <div class="min-w-0">
          <Title :said="said" size="text-6xl lg:text-8xl" @change="relay" />
          <Facts class="mt-4" :said="said" @change="relay" />
        </div>
        <button class="shrink-0 rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3 max-sm:hidden" :aria-label="__('Team')" @click="$emit('view', 'team')">
          <People :users="users" :people="teamPeople" :max="5" size="md" />
        </button>
      </div>
    </div>

    <template v-else>
      <Hero :media="said.media" :can-add="said.can_write" @open="show" @add="add">
        <template #over>
          <div class="mb-2 text-sm font-medium uppercase tracking-widest text-white-overlay-800">{{ __(said.kind) }}</div>
          <Title :said="said" on-image size="text-6xl lg:text-8xl" @change="relay" />
          <Facts class="mt-4 max-sm:hidden" :said="said" on-image @change="relay" />
        </template>
        <template #corner>
          <button class="rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3" :aria-label="__('Team')" @click="$emit('view', 'team')">
            <People :users="users" :people="teamPeople" :max="5" size="md" />
          </button>
        </template>
      </Hero>
      <Facts class="mt-4 sm:hidden" :said="said" @change="relay" />
    </template>

    <Media v-model:open="viewing" v-model:at="at" :media="said.media" :project="said.name" :can-add="said.can_write" @add="add" />
  </header>
</template>

<script setup>
import { computed, ref } from "vue";
import { Button } from "frappe-ui";

import { People, __, upload } from "../kit";
import Facts from "./Facts.vue";
import Hero from "./Hero.vue";
import Media from "./Media.vue";
import Title from "./Title.vue";

const props = defineProps({
  said: { type: Object, required: true },
});
const emit = defineEmits(["change", "media", "view"]);
const relay = (fieldname, value) => emit("change", fieldname, value);
const users = computed(() => props.said.people.map((one) => one.user));
const teamPeople = computed(() => Object.fromEntries(props.said.people.map((one) => [one.user, one])));

const viewing = ref(false);
const at = ref(0);
function show(i) {
  at.value = i;
  viewing.value = true;
}

const add = () =>
  upload("Project", props.said.name, () => emit("media"), {
    method: "onedesk.one_project.media.add",
    restrictions: { allowed_file_types: ["image/*", "video/*"] },
    allow_web_link: false,
    disable_file_browser: true,
  });
</script>
