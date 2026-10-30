// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/utils/tableMenu.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { activeEditor } from '@/apps/slides/composables/useTextEditor'
import { runTableCommand, distributeColumns, mergeCells } from '@/apps/slides/utils/tableStructure'
import { getTableSize } from '@/apps/slides/utils/tableWidths'

// the delete options go with the last row or column, matching the panel's count of 1
export const buildTableContextOptions = () => {
	const { rows, columns } = getTableSize(activeEditor.value.getHTML())

	const insertOptions = [
		{
			label: __('Row above'),
			icon: 'lucide-between-horizontal-start',
			onClick: () => runTableCommand('addRowBefore'),
		},
		{
			label: __('Row below'),
			icon: 'lucide-between-horizontal-end',
			onClick: () => runTableCommand('addRowAfter'),
		},
		{
			label: __('Column left'),
			icon: 'lucide-between-vertical-start',
			onClick: () => runTableCommand('addColumnBefore'),
		},
		{
			label: __('Column right'),
			icon: 'lucide-between-vertical-end',
			onClick: () => runTableCommand('addColumnAfter'),
		},
	]

	const modifyOptions = [
		{
			label: __('Merge cells'),
			icon: 'lucide-table-cells-merge',
			condition: () => activeEditor.value.can().mergeCells(),
			onClick: () => mergeCells(),
		},
		{
			label: __('Split cell'),
			icon: 'lucide-table-cells-split',
			condition: () => activeEditor.value.can().splitCell(),
			onClick: () => runTableCommand('splitCell'),
		},
		{
			label: __('Distribute columns'),
			icon: 'lucide-align-horizontal-distribute-center',
			onClick: () => distributeColumns(),
		},
	]

	const deleteOptions = [
		{
			label: __('Delete row'),
			icon: 'lucide-rows-3',
			condition: () => rows > 1,
			onClick: () => runTableCommand('deleteRow'),
		},
		{
			label: __('Delete column'),
			icon: 'lucide-columns-3',
			condition: () => columns > 1,
			onClick: () => runTableCommand('deleteColumn'),
		},
	]

	return [
		{ group: __('Insert'), options: insertOptions },
		{ group: __('Modify'), options: modifyOptions },
		{ group: '', options: deleteOptions },
	]
}
