<template>
  <!-- What a record is, label against value: a value may open a route, run
       `onClick`, show `avatars` (the kit's People, as a record's head shows
       them) or a `tone`. One with a `field` is that field of the record
       whose desk form is `form` (the kit's useForm), changed in place
       (FieldEdit), and not shown while the form hides it; with `blankZero`
       a 0 shows the placeholder, where 0 means none. Each label is on
       the left and its value on the right, wrapping when long: a flex row
       pushed to the end clips a long value at its start, with no ellipsis. -->
  <dl class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-6 gap-y-3.5 text-base">
    <template v-for="one in shown" :key="one.label">
      <dt class="text-ink-gray-5">{{ one.label }}</dt>
      <!-- Avatars aren't truncated: clipping the line would crop their rings. -->
      <dd class="flex min-w-0 justify-end text-end" :class="[one.avatars ? '' : '[overflow-wrap:anywhere]', one.tone === 'red' ? 'text-ink-red-5' : one.tone === 'gray' ? 'text-ink-gray-5' : 'text-ink-gray-8']">
        <FieldEdit v-if="one.field" :form="form" :field="one.field" :label="one.label" :placeholder="one.placeholder" :blank-zero="one.blankZero" @saved="emit('saved', one.field)" />
        <button v-else-if="one.avatars" class="flex items-center rounded-3 focus-visible:ring-2 focus-visible:ring-outline-gray-3" :aria-label="one.value" @click="one.onClick ? one.onClick() : go(one.route)">
          <People :users="one.avatars.map((person) => person.label)" :people="Object.fromEntries(one.avatars.map((person) => [person.label, { name: person.label, image: person.image }]))" :max="6" />
        </button>
        <button v-else-if="one.route || one.onClick" class="hover:underline" @click="one.onClick ? one.onClick() : go(one.route)">{{ one.value }}</button>
        <span v-else>{{ one.value }}</span>
      </dd>
    </template>
  </dl>
</template>

<script setup>
import { computed } from "vue";

import { go } from "./desk";
import FieldEdit from "./FieldEdit.vue";
import People from "./People.vue";

const props = defineProps({ facts: { type: Array, required: true }, form: Object });
const emit = defineEmits(["saved"]);

const shown = computed(() => props.facts.filter((one) => !one.field || (props.form && props.form.status(one.field) !== "None")));
</script>
