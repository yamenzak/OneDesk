<template>
  <!-- A section's rows on a record's page: a name with a line under it, a
       Badge and a figure, each opening its own page where it has one. -->
  <List :columns="['minmax(0,1fr)', 'auto', '7rem']" class="-mx-3 list-row-px-3">
    <ListRows :items="rows" :row-key="(item, index) => index" v-slot="{ item }">
      <ListRow :route="item.to" :href="item.href" :target="item.href ? '_blank' : undefined">
        <ListCell :class="['flex-col !items-start gap-0.5 py-1.5', item.under && 'ps-5']">
          <span class="text-base text-ink-gray-8">{{ item.title }}</span>
          <span v-if="item.line" class="text-sm text-ink-gray-5">{{ item.line }}</span>
        </ListCell>
        <ListCell><Badge v-if="item.status" :theme="item.tone" :label="item.status" /></ListCell>
        <ListCell :class="['justify-end tabular-nums text-base', item.late ? 'text-ink-red-6' : 'text-ink-gray-7']">{{ item.figure }}</ListCell>
      </ListRow>
    </ListRows>
  </List>
</template>

<script setup>
import { Badge } from "frappe-ui";
import { List, ListCell, ListRow, ListRows } from "frappe-ui/list";

defineProps({ rows: { type: Array, required: true } });
</script>
