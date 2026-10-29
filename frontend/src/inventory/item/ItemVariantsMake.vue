<template>
  <Dialog :open="open" :title="__('Make Several Variants')" size="xl" @update:open="(now) => emit('update:open', now)">
    <div class="flex flex-col gap-5">
      <p class="text-p-base text-ink-gray-6">{{ __("Pick the values to make. Every combination of them becomes a variant.") }}</p>
      <p v-if="!choices.attributes.length" class="text-base text-ink-gray-5">{{ __("This template has no attributes to choose from.") }}</p>
      <div v-for="one in choices.attributes" :key="one.attribute" class="flex flex-col gap-2">
        <div class="flex items-center justify-between gap-2">
          <span class="text-base font-medium text-ink-gray-8">{{ __(one.attribute) }}</span>
          <div v-if="one.values?.length > 1" class="flex gap-1">
            <Button variant="ghost" size="sm" :label="__('All')" @click="picked[one.attribute] = [...one.values]" />
            <Button variant="ghost" size="sm" :label="__('None')" @click="picked[one.attribute] = []" />
          </div>
        </div>
        <div v-if="one.values" class="flex flex-wrap gap-1.5">
          <Button
            v-for="value in one.values"
            :key="value"
            size="sm"
            :variant="picked[one.attribute].includes(value) ? 'solid' : 'outline'"
            :icon-left="picked[one.attribute].includes(value) ? 'lucide-check' : undefined"
            :label="value"
            :aria-pressed="picked[one.attribute].includes(value)"
            @click="toggle(one, value)"
          />
          <span v-if="!one.values.length" class="text-base text-ink-gray-5">{{ __("No values") }}</span>
        </div>
        <TextInput v-else v-model="typed[one.attribute]" :placeholder="__('Values, separated by commas')" @update:model-value="read(one)" />
        <p v-if="one.numeric" class="text-sm" :class="wrong[one.attribute]?.length ? 'text-ink-red-5' : 'text-ink-gray-5'">
          {{ wrong[one.attribute]?.length ? __("{0} is not between {1} and {2} in steps of {3}", [wrong[one.attribute].join(", "), ...one.numeric.said]) : __("From {0} to {1}, in steps of {2}", one.numeric.said) }}
        </p>
      </div>
      <Switch v-if="choices.image" v-model="picture" :label="__('Copy the Template Image')" />
      <p class="text-base" :class="tooMany ? 'text-ink-red-5' : 'text-ink-gray-7'">{{ said }}</p>
    </div>
    <template #actions>
      <div class="flex justify-end gap-2">
        <Button :label="__('Cancel')" @click="emit('update:open', false)" />
        <Button variant="solid" :label="label" :disabled="!fresh || tooMany || blocked" :loading="busy" @click="make" />
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from "vue";
import { Button, Dialog, Switch, TextInput } from "frappe-ui";

import { __, alert, call } from "../../kit";

// choices: the template's attributes, each with the values it allows (null for a
// numeric range too long to list, which is typed), and the combinations its
// variants already are (view.py, _choices).
const props = defineProps({ item: { type: String, required: true }, choices: { type: Object, required: true }, open: Boolean });
const emit = defineEmits(["update:open", "made"]);

// ERPNext refuses 600 or more at once and says 500; it makes ten or more in the background.
const MOST = 500;
const QUEUED = 10;

const picked = reactive({});
const typed = reactive({});
const wrong = reactive({});
const picture = ref(false);
const busy = ref(false);

watch(
  () => props.open,
  (now) => {
    if (!now) return;
    picture.value = false;
    for (const one of props.choices.attributes) {
      picked[one.attribute] = [];
      typed[one.attribute] = "";
      wrong[one.attribute] = [];
    }
  },
  { immediate: true }
);

function toggle(one, value) {
  const list = picked[one.attribute];
  picked[one.attribute] = list.includes(value) ? list.filter((other) => other !== value) : [...list, value];
}

// A typed value of a numeric range counts when it lies on one of its steps, as ERPNext's dialog checks it.
function onStep(range, text) {
  const value = Number(text);
  if (!Number.isFinite(value) || value < range.from || value > range.to || !(range.step > 0)) return null;
  const steps = (value - range.from) / range.step;
  return Math.abs(Math.round(steps) - steps) <= 1e-6 ? String(value) : null;
}
function read(one) {
  const good = [];
  const bad = [];
  for (const text of String(typed[one.attribute] || "").split(/[\s,]+/).filter(Boolean)) {
    const value = onStep(one.numeric, text);
    if (value === null) bad.push(text);
    else if (!good.includes(value)) good.push(value);
  }
  picked[one.attribute] = good;
  wrong[one.attribute] = bad;
}
const blocked = computed(() => Object.values(wrong).some((list) => list.length));

const same = (one, a, b) => (one.numeric ? Number(a) === Number(b) : a === b);
const chosen = computed(() => props.choices.attributes.filter((one) => picked[one.attribute]?.length));
const count = computed(() => (chosen.value.length ? chosen.value.reduce((all, one) => all * picked[one.attribute].length, 1) : 0));

// ERPNext skips a combination a variant already is (get_variant), so say how many are really new.
const already = computed(() => {
  if (!count.value) return 0;
  const attrs = chosen.value;
  return (props.choices.made || []).filter(
    (combo) => Object.keys(combo).length === attrs.length && attrs.every((one) => combo[one.attribute] !== undefined && picked[one.attribute].some((value) => same(one, value, combo[one.attribute])))
  ).length;
});
const fresh = computed(() => count.value - already.value);
const tooMany = computed(() => count.value > MOST);

const said = computed(() => {
  if (!count.value) return __("Pick at least one value.");
  if (tooMany.value) return __("That is {0} variants. Make at most {1} at a time.", [count.value, MOST]);
  if (!fresh.value) return count.value === 1 ? __("That variant already exists.") : __("All {0} of these variants already exist.", [count.value]);
  const made = already.value ? __("Makes {0} new variants. {1} of these combinations already exist and are left as they are.", [fresh.value, already.value]) : count.value === 1 ? __("Makes 1 variant.") : __("Makes {0} variants.", [count.value]);
  return count.value >= QUEUED ? `${made} ${__("They are made in the background and appear here as they are made.")}` : made;
});
const label = computed(() => (fresh.value === 1 ? __("Make 1 Variant") : fresh.value > 1 ? __("Make {0} Variants", [fresh.value]) : __("Make Variants")));

async function make() {
  const args = Object.fromEntries(chosen.value.map((one) => [one.attribute, [...picked[one.attribute]]]));
  busy.value = true;
  try {
    const got = await call("erpnext.controllers.item_variant.enqueue_multiple_variant_creation", { item: props.item, args, use_template_image: picture.value ? 1 : 0 });
    if (got === "queued") alert(__("Making {0} variants in the background", [fresh.value]), "blue");
    else alert(Number(got) === 1 ? __("1 variant made") : __("{0} variants made", [got]));
    emit("update:open", false);
    emit("made");
  } finally {
    busy.value = false;
  }
}
</script>
