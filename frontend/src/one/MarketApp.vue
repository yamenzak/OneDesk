<template>
  <div class="mt-4">
    <Button variant="ghost" icon-left="lucide-arrow-left" :label="__('All Apps')" @click="emit('back')" />

    <div class="mt-4 flex flex-wrap items-start gap-4">
      <span class="flex size-16 shrink-0 items-center justify-center rounded-5 bg-surface-gray-2 text-ink-gray-7"><Mark :name="app.mark" class="icon size-10" /></span>
      <div class="flex min-w-0 flex-1 flex-col gap-1">
        <h1 class="text-2xl font-semibold text-ink-gray-9">{{ app.name }}</h1>
        <p class="text-base text-ink-gray-6">{{ app.line }}</p>
      </div>
      <div class="flex items-center gap-2">
        <Badge v-if="app.on" :label="__('On')" theme="green" size="md" />
        <Button v-if="app.may_install" variant="solid" :label="__('Install')" :loading="busy" @click="emit('turn', app, true)" />
        <Button v-else-if="app.may_turn_off" :label="__('Turn Off')" :loading="busy" @click="leaving = true" />
      </div>
    </div>
    <p v-if="held" class="mt-3 text-sm text-ink-gray-5">{{ held }}</p>

    <div v-if="app.media.length" class="-mx-1 mt-6 flex snap-x gap-3 overflow-x-auto px-1 pb-2">
      <template v-for="(one, index) in app.media" :key="one.src">
        <video
          v-if="one.video"
          :src="sources[index] || one.src"
          class="h-72 shrink-0 snap-start rounded-4 border border-outline-gray-1"
          autoplay
          loop
          muted
          playsinline
          :aria-label="__('{0} on the demo company', [app.name])"
          @error="sources[index] = one.here"
        />
        <img
          v-else
          :src="sources[index] || one.src"
          :alt="__('{0} on the demo company', [app.name])"
          class="h-72 shrink-0 snap-start rounded-4 border border-outline-gray-1"
          loading="lazy"
          @error="sources[index] = one.here"
        />
      </template>
    </div>
    <div v-else class="mt-6 flex h-48 items-center justify-center rounded-4 bg-surface-gray-1 text-ink-gray-5">
      <Mark :name="app.mark" class="icon size-20" />
    </div>

    <div class="mt-8 grid gap-8 lg:grid-cols-[minmax(0,1fr)_20rem]">
      <div>
        <p class="text-base leading-relaxed text-ink-gray-8">{{ app.pitch }}</p>
        <template v-if="app.brings.length">
          <h2 class="mt-6 text-lg font-semibold text-ink-gray-9">{{ __("What It Brings") }}</h2>
          <ul class="mt-3 flex flex-col gap-2">
            <li v-for="line in app.brings" :key="line" class="flex items-start gap-2 text-base text-ink-gray-8">
              <span class="lucide-check mt-0.5 size-4 shrink-0 text-ink-gray-5" aria-hidden="true" />
              <span>{{ line }}</span>
            </li>
          </ul>
        </template>
      </div>

      <dl class="flex flex-col gap-4 rounded-4 border border-outline-gray-1 bg-surface-elevation-2 px-4 py-4 text-base">
        <div>
          <dt class="text-sm text-ink-gray-5">{{ __("Plan") }}</dt>
          <dd class="mt-0.5 text-ink-gray-8">{{ app.plan.included ? __("Included in your plan") : app.plan.needs ? __("Needs the {0} plan", [app.plan.needs]) : __("Not in your plan") }}</dd>
        </div>
        <div>
          <dt class="text-sm text-ink-gray-5">{{ __("Credits") }}</dt>
          <dd v-if="app.credits.length" class="mt-0.5 flex flex-col gap-1 text-ink-gray-8">
            <span v-for="line in app.credits" :key="line">{{ line }}</span>
          </dd>
          <dd v-else class="mt-0.5 text-ink-gray-8">{{ __("Uses no credits") }}</dd>
        </div>
        <div v-if="app.needs.length">
          <dt class="text-sm text-ink-gray-5">{{ __("Needs") }}</dt>
          <dd class="mt-0.5 text-ink-gray-8">{{ app.on ? andList(app.needs) : __("{0}, turned on with it", [andList(app.needs)]) }}</dd>
        </div>
        <div v-if="app.needed_by.length">
          <dt class="text-sm text-ink-gray-5">{{ __("Needed By") }}</dt>
          <dd class="mt-0.5 text-ink-gray-8">{{ andList(app.needed_by) }}</dd>
        </div>
      </dl>
    </div>

    <Dialog v-model:open="leaving" :title="__('Turn Off {0}?', [app.name])" size="md">
      <p class="text-base text-ink-gray-7">{{ __("It leaves the rail and search for everybody. Its records stay, and links to them still open.") }}</p>
      <template #actions>
        <div class="flex justify-end">
          <Button variant="solid" theme="red" :label="__('Turn Off')" :loading="busy" @click="(leaving = false), emit('turn', app, false)" />
        </div>
      </template>
    </Dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from "vue";
import { Badge, Button, Dialog } from "frappe-ui";

import { Mark, __, andList } from "../kit";

const props = defineProps({ app: { type: Object, required: true }, busy: Boolean });
const emit = defineEmits(["back", "turn"]);

const leaving = ref(false);
const sources = reactive({});

const held = computed(() => {
  if (props.app.always) return props.app.kept || __("Always on.");
  if (props.app.on && props.app.kept) return __("Can't be turned off. {0}", [props.app.kept]);
  if (props.app.on && props.app.needed_by.length) return __("Needed by {0}, so it can't be turned off.", [andList(props.app.needed_by)]);
  return "";
});
</script>
