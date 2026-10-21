<!-- Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/components/FDialogs.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
  <div>
    <Dialog
      v-for="dialog in dialogs"
      :key="dialog.key"
      v-model:open="dialog.modelValue"
      :options="dialog.options"
      @close="dialog.remove"
    >
      <component v-if="dialog.options.component" :is="dialog.options.component" />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { useDialogs } from '@/apps/writer/utils/dialogs'
import { Dialog } from 'frappe-ui'

const dialogs = useDialogs()
</script>
