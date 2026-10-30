// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/composables/useNavigationPanel.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { ref } from 'vue'
import { activeElementIds, activeElement } from '@/apps/slides/stores/element'

const isNavigationPanelOpen = ref(true)

const toggleNavigationPanel = (e) => {
	if (!activeElementIds.value.length || e.type === 'click') {
		isNavigationPanelOpen.value = !isNavigationPanelOpen.value
	}
}

export const useNavigationPanel = () => {
	return {
		isNavigationPanelOpen,
		toggleNavigationPanel,
	}
}
