<!-- Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/components/NewVersionDialog.vue. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md. -->
<template>
  <FormControl v-model="versionName" autofocus :label="__('Name')" autocomplete="off">
    <template #prefix>
      <LucideVersion class="size-4" />
    </template>
  </FormControl>
  <Button type="submit" :label="__('Create')" variant="solid" class="w-full mt-5" :loading="document.newVersion.loading"
    :disabled="!versionName" @click="
      async () => {
        const version = await document.newVersion.submit({
          data,
          title: versionName,
        })
        clearDialogs()
      }
    " />
</template>
<script setup>
import { ref } from 'vue'
import { Button, FormControl } from 'frappe-ui'
import { clearDialogs } from '@/apps/writer/utils/dialogs'
import LucideVersion from '~icons/lucide/git-pull-request-create'

// One: the page draws the history panel again after a version is named,
// so the made version isn't pushed onto a list here.
const versionName = ref('')
const props = defineProps({
  data: String,
  document: Object,
})
</script>
