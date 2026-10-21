// Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/composables/useCollaborationUsers.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { ref } from 'vue'

type CollaborationUser = Record<string, unknown> & {
  clientId: number
  id?: string
  name?: string
  avatar?: string
  color?: string
}

type CollaborationAwareness = {
  getStates: () => Map<
    number,
    { user?: Record<string, unknown> } | null | undefined
  >
  on: (event: 'update', listener: () => void) => void
  off: (event: 'update', listener: () => void) => void
}

export function useCollaborationUsers(awareness: CollaborationAwareness) {
  const users = ref<CollaborationUser[]>([])

  const syncUsers = () => {
    users.value = Array.from(awareness.getStates(), ([clientId, state]) =>
      state?.user ? { clientId, ...state.user } : null,
    ).filter((user): user is CollaborationUser => user !== null)
  }

  awareness.on('update', syncUsers)
  syncUsers()

  const cleanup = () => {
    awareness.off('update', syncUsers)
    users.value = []
  }

  return { users, cleanup }
}
