// Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/utils/dialogs.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { ref, reactive } from 'vue'
import type { DialogProps } from 'frappe-ui/src/components/Dialog/types'

interface DialogOptions extends DialogProps {
  key: string
  modelValue: boolean
}

type UserDialogOptions = Omit<DialogOptions, 'key' | 'modelValue'>

const dialogs = ref<DialogOptions[]>([])

export function createDialog(options: UserDialogOptions) {
  const dialog = reactive<DialogOptions>({
    key: 'dialog-' + dialogs.value.length,
    modelValue: false,
    options,
  })

  dialog.remove = () => {
    dialogs.value = dialogs.value.filter((d) => d.key !== dialog.key)
  }

  dialogs.value.push(dialog)

  // open after mount
  setTimeout(() => {
    dialog.modelValue = true
  }, 0)

  return dialog
}

export function useDialogs() {
  return dialogs
}

export function clearDialogs() {
  dialogs.value = []
}
