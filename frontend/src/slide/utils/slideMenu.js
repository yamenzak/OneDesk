// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/utils/slideMenu.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { deleteSlide, duplicateSlide } from '@/apps/slides/stores/slide'

export const buildSlideContextOptions = ({ index, openLayoutDialog }) => [
	{
		label: __('New'),
		icon: 'lucide-plus',
		onClick: () => openLayoutDialog(index),
	},
	{
		label: __('Duplicate'),
		icon: 'lucide-copy',
		onClick: () => duplicateSlide(index),
	},
	{
		label: __('Delete'),
		icon: 'lucide-trash-2',
		theme: 'red',
		onClick: () => deleteSlide(false, index),
	},
]
