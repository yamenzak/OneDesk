<template>
  <!-- The item's first two barcodes, drawn by frappe's Barcode control. Any
       of them opens Manage Barcodes, where they are added, changed and put
       in order; the first two are the ones shown here. -->
  <div class="flex flex-col items-end gap-2">
    <button
      v-for="one in shown"
      :key="one.barcode"
      class="w-48 rounded-3 border border-outline-gray-1 bg-white-overlay-900 px-3 pb-1 pt-2 text-left focus-visible:ring-2 focus-visible:ring-outline-gray-3"
      :class="canWrite ? 'hover:border-outline-gray-3' : 'cursor-default'"
      :aria-label="__('Barcode {0}', [one.barcode])"
      @click="manage"
    >
      <div class="h-14" v-html="one.svg" />
    </button>
    <Button v-if="canWrite || more" variant="ghost" size="sm" :label="more ? __('{0} More', [more]) : __('Manage Barcodes')" @click="manage" />
  </div>
</template>

<script setup>
// The barcodes in an item's head (one_inventory/barcodes.py). Each is drawn
// by frappe.ui.form.ControlBarcode, the control desk's Barcode field uses, in
// the format its ERPNext type names, or Code 128 when it has none or does
// not fit it.
import { computed } from "vue";
import { Button } from "frappe-ui";

import { __, alert, barcode, call, dialog as deskDialog, docfield } from "../kit";

const props = defineProps({
  item: { type: String, required: true },
  barcodes: { type: Array, default: () => [] },
  canWrite: Boolean,
});
const emit = defineEmits(["changed"]);

// ERPNext's barcode types, in the formats JsBarcode draws.
const FORMAT = {
  EAN: "EAN",
  "EAN-13": "EAN13",
  "EAN-8": "EAN8",
  ISBN: "EAN13",
  "ISBN-13": "EAN13",
  JAN: "EAN13",
  GTIN: "EAN13",
  "UPC-A": "UPC",
  UPC: "UPC",
  "CODE-39": "CODE39",
  "GTIN-14": "ITF14",
};

const SIZE = { height: 34, width: 1.4, fontSize: 12, margin: 0 };
const drawn = (value, format) => barcode(value, format, SIZE);

const draw = (one) => drawn(one.barcode, FORMAT[one.barcode_type] || "CODE128") || drawn(one.barcode, "CODE128") || "";

const shown = computed(() => props.barcodes.slice(0, 2).map((one) => ({ ...one, svg: draw(one) })));
const more = computed(() => Math.max(props.barcodes.length - 2, 0));

async function manage() {
  if (!props.canWrite) return;
  const types = (await docfield("Item Barcode", "barcode_type"))?.options || "";
  const dialog = deskDialog({
    title: __("Barcodes"),
    size: "large",
    fields: [
      {
        fieldtype: "Table",
        fieldname: "rows",
        description: __("The first two show on the item's page. Drag a row to move it."),
        in_place_edit: true,
        data: props.barcodes.map((one) => ({ barcode: one.barcode, barcode_type: one.barcode_type, uom: one.uom })),
        fields: [
          { fieldtype: "Data", fieldname: "barcode", label: __("Barcode"), in_list_view: 1, reqd: 1, columns: 4 },
          { fieldtype: "Select", fieldname: "barcode_type", label: __("Barcode Type"), options: types, in_list_view: 1, columns: 3 },
          { fieldtype: "Link", fieldname: "uom", label: __("Unit"), options: "UOM", in_list_view: 1, columns: 3 },
        ],
      },
    ],
    primary_action_label: __("Save"),
    primary_action: async (values) => {
      const rows = [...(values.rows || [])].sort((a, b) => a.idx - b.idx);
      await call("onedesk.one_inventory.barcodes.save", { item: props.item, rows });
      dialog.hide();
      alert(__("Saved"));
      emit("changed");
    },
  });
  dialog.show();
}
</script>
