<template>
  <!-- The project's head: its Featured Media turning behind its name
       (Hero.vue), then what its kind is watched by, changed right here
       (Facts.vue). -->
  <header class="pt-6">
    <template v-if="!said.media.length">
      <div class="flex items-center gap-3">
        <Title :said="said" @change="relay" />
        <Button v-if="said.can_write" class="ms-auto" variant="ghost" icon-left="lucide-image-plus" :label="__('Add Cover')" @click="add" />
      </div>
      <Facts class="mt-3" :said="said" :progress="progress" @change="relay" />
    </template>

    <template v-else>
      <Hero :media="said.media" :can-add="said.can_write" @open="show" @add="add">
        <template #over>
          <div class="mb-2 text-sm font-medium uppercase tracking-widest text-white-overlay-800">{{ __(said.kind) }}</div>
          <Title :said="said" on-image size="text-6xl lg:text-8xl" @change="relay" />
        </template>
      </Hero>
      <Facts class="mt-4" :said="said" :progress="progress" @change="relay" />
    </template>

    <Media v-model:open="viewing" v-model:at="at" :media="said.media" :project="said.name" :can-add="said.can_write" @add="add" />
  </header>
</template>

<script setup>
import { ref } from "vue";
import { Button } from "frappe-ui";

import { __, upload } from "../kit";
import Facts from "./Facts.vue";
import Hero from "./Hero.vue";
import Media from "./Media.vue";
import Title from "./Title.vue";

const props = defineProps({
  said: { type: Object, required: true },
  progress: { type: Number, default: null },
});
const emit = defineEmits(["change", "media"]);
const relay = (fieldname, value) => emit("change", fieldname, value);

const viewing = ref(false);
const at = ref(0);
function show(i) {
  at.value = i;
  viewing.value = true;
}

// frappe's upload dialog, sending what is picked to the project's Featured
// Media (one_project/media.py `add`).
const add = () =>
  upload("Project", props.said.name, () => emit("media"), {
    method: "onedesk.one_project.media.add",
    restrictions: { allowed_file_types: ["image/*", "video/*"] },
    allow_web_link: false,
    disable_file_browser: true,
  });
</script>
