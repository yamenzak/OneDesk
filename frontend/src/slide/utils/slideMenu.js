// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/utils/slideMenu.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { deleteSlide, duplicateSlide, slides } from '@/apps/slides/stores/slide'
import { presentationDoc } from '@/apps/slides/stores/presentation' // One
import { saveToLibrary } from '@/apps/slides/shim/libraryKeep.js' // One: VENDORED.md

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
	// One: a manager keeps a slide in the company's slide library
	...(presentationDoc.value?.can_template
		? [{ label: __('Save to Library'), icon: 'lucide-library', onClick: () => saveToLibrary(slides.value[index]) }]
		: []),
	{
		label: __('Delete'),
		icon: 'lucide-trash-2',
		theme: 'red',
		onClick: () => deleteSlide(false, index),
	},
]
