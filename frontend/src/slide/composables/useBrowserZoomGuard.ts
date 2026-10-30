// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/composables/useBrowserZoomGuard.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { onActivated, onBeforeUnmount, onDeactivated, onMounted } from 'vue'

const blockBrowserZoom = (e: WheelEvent) => {
	if (e.ctrlKey || e.metaKey) e.preventDefault()
}

const addGuard = () =>
	window.addEventListener('wheel', blockBrowserZoom, { passive: false, capture: true })

const removeGuard = () => window.removeEventListener('wheel', blockBrowserZoom, { capture: true })

export const useBrowserZoomGuard = () => {
	onMounted(addGuard)
	onActivated(addGuard)
	onDeactivated(removeGuard)
	onBeforeUnmount(removeGuard)
}
