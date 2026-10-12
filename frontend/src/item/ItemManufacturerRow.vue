<template>
  <!-- Who makes the item and their part number, the Item Manufacturer's own
       field changed in place on its own form, out of sight. The default is
       the one ERPNext puts on every order and receipt line. -->
  <li class="flex gap-3 py-2.5">
    <div class="min-w-0 flex-1">
      <div class="flex min-w-0 items-center gap-2">
        <button type="button" class="truncate rounded-2 text-base text-ink-gray-8 hover:underline focus-visible:ring-2 focus-visible:ring-outline-gray-3" @click="go(`/desk/manufacturer/${encodeURIComponent(maker.manufacturer)}`)">
          {{ maker.manufacturer }}
        </button>
        <Badge v-if="maker.is_default" :label="__('Default')" theme="blue" size="sm" />
      </div>
      <div class="mt-1 flex items-center gap-1.5 whitespace-nowrap text-sm text-ink-gray-5">
        {{ __("Part Number") }}
        <FieldEdit :form="form" field="manufacturer_part_no" :label="__('Part Number')" class="text-ink-gray-8" @saved="emit('changed')" />
      </div>
    </div>
    <Dropdown v-if="actions.length" :options="actions" placement="right">
      <template #trigger><Button variant="ghost" icon="lucide-ellipsis" :aria-label="__('Actions')" /></template>
    </Dropdown>
  </li>
</template>

<script setup>
import { computed } from "vue";
import { Badge, Button, Dropdown } from "frappe-ui";

import { FieldEdit, __, go, useForm } from "../kit";

const props = defineProps({
  // The Item Manufacturer row as the page read it.
  maker: { type: Object, required: true },
});
const emit = defineEmits(["changed"]);

const form = useForm("Item Manufacturer", computed(() => props.maker.name));

// Make Default sets the record's own switch; ERPNext then clears the others
// and puts it on the item.
const actions = computed(() =>
  !props.maker.is_default && form.status("is_default") === "Write"
    ? [{ label: __("Make Default"), icon: "lucide-star", onClick: makeDefault }]
    : []
);

async function makeDefault() {
  await form.set("is_default", 1);
  if (await form.save()) emit("changed");
}
</script>
