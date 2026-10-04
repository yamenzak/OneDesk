<template>
  <!-- The project's head, laid out for its kind: the cover from its Featured
       Media with the rest beside it, its name, and what the kind is
       watched by, changed right here. -->
  <header class="pt-6">
    <div v-if="said.media.length" class="relative mb-5 h-40 overflow-hidden rounded-7 bg-surface-gray-2 sm:h-52">
      <button class="block size-full" :aria-label="__('Featured Media')" @click="show(0)">
        <img v-if="banner.kind === 'photo'" :src="banner.url" :alt="banner.title" class="size-full object-cover" />
        <video v-else :src="`${banner.url}#t=0.1`" muted preload="metadata" class="size-full object-cover" />
      </button>
      <div class="absolute bottom-3 end-3 flex items-center gap-2">
        <button v-for="(one, i) in more" :key="one.name" class="size-12 overflow-hidden rounded-4 ring-2 ring-outline-white max-sm:hidden" :aria-label="one.title" @click="show(i + 1)">
          <Thumb :item="one" />
        </button>
        <Button v-if="said.media.length > 1" :label="__('{0} Photos and Videos', [said.media.length])" @click="show(0)" />
        <Button v-else-if="said.can_write" icon-left="lucide-image-plus" :label="__('Add Photos')" @click="add" />
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <span class="flex size-9 shrink-0 items-center justify-center rounded-5 bg-surface-gray-2 text-ink-gray-7">
        <span :class="kindIcon" class="size-5" />
      </span>
      <input
        v-if="editing"
        ref="nameInput"
        v-model="name"
        class="min-w-0 flex-1 rounded-3 border-0 bg-surface-gray-2 px-2 py-0.5 text-2xl font-semibold text-ink-gray-9 focus:ring-2 focus:ring-outline-gray-3"
        :aria-label="__('Project Name')"
        @keydown.enter="saveName"
        @keydown.esc="editing = false"
        @blur="saveName"
      />
      <h1 v-else class="min-w-0 truncate text-2xl font-semibold text-ink-gray-9" :class="said.can_write && 'cursor-text rounded-3 hover:bg-surface-gray-2'" @click="startEditing">
        {{ said.title }}
      </h1>
      <Badge :label="__(said.kind)" theme="gray" size="md" />
      <Button v-if="!said.media.length && said.can_write" class="ms-auto" variant="ghost" icon-left="lucide-image-plus" :label="__('Add Cover')" @click="add" />
    </div>

    <div class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-base text-ink-gray-6">
      <Pill :value="said.status" :options="['Open', 'Completed', 'Cancelled']" :colors="PROJECT_STATUS" :label="__('Status')" :readonly="!said.can_write" @change="(v) => $emit('change', 'status', v)" />
      <Pill :value="said.health" :options="['On Track', 'At Risk', 'Off Track']" :colors="HEALTH" :label="__('Health')" :empty="__('Set Health')" :readonly="!said.can_write" @change="(v) => $emit('change', 'one_health', v)" />
      <button v-if="said.customer" class="flex items-center gap-1.5 hover:text-ink-gray-9" @click="go(`/desk/customer/${said.customer}`)">
        <span class="lucide-building size-4 text-ink-gray-5" />{{ said.customer_name || said.customer }}
      </button>
      <button v-if="said.kind === 'Fixed Price' && said.contract" class="flex items-center gap-1.5 hover:text-ink-gray-9" @click="go(`/desk/sales-order/${said.contract}`)">
        <span class="lucide-file-signature size-4 text-ink-gray-5" />{{ said.contract }}
      </button>
      <template v-if="said.kind === 'Retainer'">
        <span v-if="said.starts" class="flex items-center gap-1.5"><span class="lucide-calendar size-4 text-ink-gray-5" />{{ __("Since {0}", [date(said.starts)]) }}</span>
        <span v-if="said.monthly_hours" class="flex items-center gap-1.5"><span class="lucide-timer size-4 text-ink-gray-5" />{{ __("{0} h a month", [said.monthly_hours]) }}</span>
      </template>
      <span v-else-if="dates" class="flex items-center gap-1.5"><span class="lucide-calendar size-4 text-ink-gray-5" />{{ dates }}</span>
      <span v-if="said.kind === 'Internal' && due" class="flex items-center gap-1.5" :class="said.days_left < 0 && 'text-ink-red-5'"><span class="lucide-flag size-4" :class="said.days_left < 0 ? 'text-ink-red-5' : 'text-ink-gray-5'" />{{ due }}</span>
      <span v-if="said.manager_name" class="flex items-center gap-1.5">
        <Avatar :label="said.manager_name" size="xs" />{{ said.manager_name }}
      </span>
      <span v-if="said.kind !== 'Retainer' && progress !== null" class="flex items-center gap-2 whitespace-nowrap">
        <div class="w-24"><Progress :value="progress" size="md" /></div>
        <span class="tabular-nums">{{ __("{0}% done", [progress]) }}</span>
      </span>
      <div class="ms-auto">
        <People :users="said.team.map((one) => one.user)" :people="teamPeople" :max="6" size="md" />
      </div>
    </div>

    <Media v-model:open="viewing" v-model:at="at" :media="said.media" :project="said.name" :can-add="said.can_write" @add="add" />
  </header>
</template>

<script setup>
import { computed, nextTick, ref } from "vue";
import { Avatar, Badge, Button, Progress } from "frappe-ui";

import { People, Pill, __, date, go, upload } from "../kit";
import { HEALTH, PROJECT_STATUS } from "./colors";
import Media from "./Media.vue";
import Thumb from "./Thumb.vue";

const props = defineProps({
  said: { type: Object, required: true },
  progress: { type: Number, default: null },
});
const emit = defineEmits(["change", "media"]);

const KIND_ICONS = { "Fixed Price": "lucide-file-text", "Time and Materials": "lucide-clock", Retainer: "lucide-repeat", Internal: "lucide-building" };
const kindIcon = computed(() => KIND_ICONS[props.said.kind] || "lucide-folder");
const dates = computed(() => [props.said.starts, props.said.ends].filter(Boolean).map(date).join(" – "));
const due = computed(() => {
  const left = props.said.days_left;
  if (left === null || left === undefined) return "";
  if (left < 0) return __("{0} days late", [-left]);
  return left === 0 ? __("Due today") : __("Due in {0} days", [left]);
});
const teamPeople = computed(() => Object.fromEntries(props.said.team.map((one) => [one.user, one])));

// The cover is the newest photo; a project with only videos opens on one.
const banner = computed(() => props.said.media.find((one) => one.url === props.said.cover) || props.said.media[0]);
const more = computed(() => props.said.media.filter((one) => one !== banner.value).slice(0, 3));
const viewing = ref(false);
const at = ref(0);
function show(i) {
  at.value = props.said.media.indexOf(i === 0 ? banner.value : more.value[i - 1]);
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

const editing = ref(false);
const name = ref("");
const nameInput = ref(null);
function startEditing() {
  if (!props.said.can_write) return;
  name.value = props.said.title;
  editing.value = true;
  nextTick(() => nameInput.value?.select());
}
function saveName() {
  if (!editing.value) return;
  editing.value = false;
  const now = name.value.trim();
  if (now && now !== props.said.title) emit("change", "project_name", now);
}
</script>
