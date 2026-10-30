<template>
  <aside class="w-full shrink-0 border-t border-outline-gray-1 md:w-80 md:overflow-y-auto md:border-s md:border-t-0">
    <template v-if="d.chosenBlocks.value.length > 1">
      <header class="flex items-center gap-1 border-b border-outline-gray-1 px-4 py-3">
        <h3 class="me-auto text-base font-medium text-ink-gray-9">{{ __("{0} Blocks", [d.chosenBlocks.value.length]) }}</h3>
      </header>
      <Arrange />
      <Section :title="sections.effects">
        <Field :spec="props_.opacity" :model-value="shared('opacity')" :disabled="!d.writable.value" @update:model-value="(v) => setAll('opacity', v)" />
      </Section>
    </template>

    <template v-else-if="one">
      <header class="flex items-center gap-1 border-b border-outline-gray-1 px-4 py-3">
        <h3 class="me-auto truncate text-base font-medium text-ink-gray-9">{{ one.name || kinds[one.kind].label }}</h3>
        <Button v-if="one.locked" size="sm" variant="ghost" icon="lucide-lock" :tooltip="__('Unlock')" :aria-label="__('Unlock')" @click="d.set(one, 'locked', 0)" />
      </header>
      <Arrange />
      <Section v-for="name in kinds[one.kind].sections" :key="name" :title="sections[name]" :open="name !== 'advanced' && name !== 'shadow'">
        <template v-for="prop in fieldsOf(name)" :key="prop">
          <Field
            :spec="props_[prop]"
            :model-value="one[prop]"
            :disabled="!d.writable.value || Boolean(one.locked)"
            @update:model-value="(v) => d.set(one, prop, v)"
            @upload="uploadTo(one, prop)"
          />
        </template>
        <Button v-if="name === 'image' && oneaiOn() && d.writable.value" :label="__('Make with OneAI')" icon-left="lucide-sparkles" :loading="drawing" @click="pictureWithAi(one)" />
        <p v-if="name === 'advanced'" class="text-xs text-ink-gray-5">{{ __("Any of the usual CSS properties, one per line, such as text-shadow or transform. Addresses are not allowed.") }}</p>
      </Section>
    </template>

    <template v-else-if="d.slide.value">
      <header class="flex items-center gap-1 border-b border-outline-gray-1 px-4 py-3">
        <h3 class="me-auto text-base font-medium text-ink-gray-9">{{ __("Slide") }}</h3>
        <Button variant="ghost" size="sm" icon="lucide-arrow-up" :tooltip="__('Move Up')" :aria-label="__('Move Up')" :disabled="!d.writable.value" @click="emit('move', -1)" />
        <Button variant="ghost" size="sm" icon="lucide-arrow-down" :tooltip="__('Move Down')" :aria-label="__('Move Down')" :disabled="!d.writable.value" @click="emit('move', 1)" />
        <Button variant="ghost" size="sm" icon="lucide-trash-2" :tooltip="__('Remove Slide')" :aria-label="__('Remove Slide')" :disabled="!d.writable.value" @click="emit('remove')" />
      </header>
      <Section :title="__('Slide')">
        <Field :spec="{ type: 'text', max: 140, label: __('Title') }" :model-value="slide.title" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'title', v)" />
        <Field :spec="kindSpec" :model-value="slide.kind" :disabled="!d.writable.value" @update:model-value="kindChanged" />
        <Field :spec="{ type: 'number', min: 2, max: 3600, step: 1, unit: 's', label: __('Seconds') }" :model-value="slide.duration" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'duration', v)" />
        <Field :spec="{ type: 'check', label: __('Paused') }" :model-value="slide.paused" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'paused', v)" />
        <div class="grid grid-cols-2 gap-2">
          <FormControl :model-value="slide.from_date" :label="__('Shown From')" type="date" size="sm" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'from_date', v)" />
          <FormControl :model-value="slide.to_date" :label="__('Shown Until')" type="date" size="sm" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'to_date', v)" />
        </div>
      </Section>

      <Section v-if="design" :title="__('Background')">
        <template v-for="(spec, prop) in schema.slide" :key="prop">
          <Field
            v-if="prop !== 'angle' || design.background2"
            :spec="spec"
            :model-value="design[prop]"
            :disabled="!d.writable.value"
            @update:model-value="(v) => d.set(design, prop, v)"
            @upload="uploadTo(design, prop)"
          />
        </template>
      </Section>

      <Section v-else-if="slide.kind === 'Design'" :title="__('Design')">
        <p class="text-sm text-ink-gray-5">{{ __("This slide was written as code, so it is shown here but can't be moved block by block.") }}</p>
        <Button :label="__('Start Again on the Canvas')" icon-left="lucide-pen-tool" :disabled="!d.writable.value" @click="emit('canvas')" />
      </Section>

      <Section v-else-if="slide.kind === 'Image' || slide.kind === 'Video'" :title="kinds_[slide.kind]">
        <Field :spec="{ type: 'file', label: __('File') }" :model-value="slide.file" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'file', v)" @upload="uploadTo(slide, 'file', slide.kind === 'Image' ? 'image/*' : 'video/*')" />
        <Field v-if="slide.kind === 'Image'" :spec="fitSpec" :model-value="slide.fit" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'fit', v)" />
        <Button v-if="slide.kind === 'Video' && oneaiOn() && d.writable.value" :label="__('Make a Video with OneAI')" icon-left="lucide-sparkles" @click="emit('video')" />
      </Section>

      <Section v-else-if="slide.kind === 'Web Page'" :title="kinds_['Web Page']">
        <Field :spec="{ type: 'text', max: 1000, label: __('Address') }" :model-value="slide.url" :disabled="!d.writable.value" @update:model-value="(v) => d.set(slide, 'url', v)" />
      </Section>
    </template>
  </aside>
</template>

<script setup>
import { computed, defineComponent, h, ref } from "vue";
import { Button, FormControl } from "frappe-ui";

import { __, call, oneaiOn, prompt, upload } from "../../kit";
import Field from "./Field.vue";
import { useDesigner } from "./store";

const emit = defineEmits(["move", "remove", "canvas", "video"]);
const d = useDesigner();
const drawing = ref(false);

const schema = computed(() => d.s.schema);
const props_ = computed(() => schema.value.properties);
const kinds = computed(() => schema.value.kinds);
const sections = computed(() => schema.value.sections);
const one = computed(() => d.only.value);
const slide = computed(() => d.slide.value);
const design = computed(() => d.design.value);

const kinds_ = { Image: __("Image"), Video: __("Video"), "Web Page": __("Web Page"), Design: __("Design") };
const kindSpec = { type: "choice", label: __("Kind"), options: Object.keys(kinds_), labels: Object.values(kinds_) };
const fitSpec = { type: "choice", label: __("Fit"), options: ["Cover", "Contain"], labels: [__("Fill"), __("Fit Inside")] };

// What a property is worth showing for, given the rest of the block: a fade's
// angle only once it fades, a border's colour only once it has a width.
const WHEN = {
  angle: (b) => b.fill2,
  fill2: (b) => b.fill,
  stroke_colour: (b) => b.stroke > 0 || (b.kind === "shape" && b.shape === "line"),
  stroke_style: (b) => b.stroke > 0,
  radius: (b) => !(b.kind === "shape" && b.shape !== "rectangle"),
  shadow_x: (b) => b.shadow_colour,
  shadow_y: (b) => b.shadow_colour,
  shadow_blur: (b) => b.shadow_colour,
};

function fieldsOf(section) {
  const b = one.value;
  return Object.keys(props_.value).filter((prop) => prop in b && props_.value[prop].section === section && (!WHEN[prop] || WHEN[prop](b)));
}

function shared(prop) {
  const values = [...new Set(d.chosenBlocks.value.map((b) => b[prop]))];
  return values.length === 1 ? values[0] : "";
}

function setAll(prop, value) {
  d.remember(`all:${prop}`);
  for (const b of d.chosenBlocks.value) if (!b.locked) b[prop] = value;
}

function kindChanged(kind) {
  d.set(slide.value, "kind", kind);
  if (kind === "Design" && !slide.value.design && !slide.value.html) slide.value.design = d.blank();
  d.choose([]);
}

function uploadTo(target, key, types = "image/*") {
  upload(null, null, (file) => d.set(target, key, file.file_url), {
    allow_multiple: false,
    make_attachments_public: true,
    restrictions: { allowed_file_types: [types] },
  });
}

function pictureWithAi(b) {
  prompt(
    [{ fieldname: "description", fieldtype: "Small Text", label: __("What it shows"), reqd: 1 }],
    async ({ description }) => {
      drawing.value = true;
      try {
        d.set(b, "src", await call("onedesk.one_display.make.picture", { description }));
      } finally {
        drawing.value = false;
      }
    },
    __("Make a Picture"),
    __("Make"),
  );
}

// A heading that folds its section away.
const Section = defineComponent({
  props: { title: String, open: { type: Boolean, default: true } },
  setup(p, { slots }) {
    const shown = ref(p.open);
    return () =>
      h("section", { class: "border-b border-outline-gray-1" }, [
        h(
          "button",
          { type: "button", class: "flex w-full items-center px-4 py-2.5 text-start text-sm font-medium text-ink-gray-8 hover:bg-surface-gray-1", onClick: () => (shown.value = !shown.value) },
          [h("span", { class: "me-auto" }, p.title), h("span", { class: "text-xs text-ink-gray-5" }, shown.value ? "−" : "+")],
        ),
        shown.value ? h("div", { class: "flex flex-col gap-2.5 px-4 pb-4" }, slots.default?.()) : null,
      ]);
  },
});

// Lining blocks up: with each other when several are chosen, with the slide
// when one is.
const Arrange = defineComponent({
  setup() {
    const tools = [
      ["left", "lucide-align-start-vertical", __("Align Left")],
      ["centre", "lucide-align-center-vertical", __("Align Centre")],
      ["right", "lucide-align-end-vertical", __("Align Right")],
      ["top", "lucide-align-start-horizontal", __("Align Top")],
      ["middle", "lucide-align-center-horizontal", __("Align Middle")],
      ["bottom", "lucide-align-end-horizontal", __("Align Bottom")],
    ];
    return () =>
      h("div", { class: "flex flex-wrap items-center gap-0.5 border-b border-outline-gray-1 px-3 py-2" }, [
        ...tools.map(([how, icon, label]) =>
          h(Button, { size: "sm", variant: "ghost", icon, tooltip: label, "aria-label": label, disabled: !d.writable.value, onClick: () => d.align(how) }),
        ),
        d.chosenBlocks.value.length > 2
          ? [
              h(Button, { size: "sm", variant: "ghost", icon: "lucide-align-horizontal-space-around", tooltip: __("Space Evenly Across"), "aria-label": __("Space Evenly Across"), onClick: () => d.distribute("across") }),
              h(Button, { size: "sm", variant: "ghost", icon: "lucide-align-vertical-space-around", tooltip: __("Space Evenly Down"), "aria-label": __("Space Evenly Down"), onClick: () => d.distribute("down") }),
            ]
          : null,
      ]);
  },
});
</script>
