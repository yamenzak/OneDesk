// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/utils/toolbarTools.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { __ } from '@/apps/slides/shim/words.js' // One: Suite's words through the desk's translations, VENDORED.md
import { h } from 'vue'

import { pendingShapeType, pendingShapePreset } from '@/apps/slides/stores/element'

const armTool = (shapeType, preset = {}) => {
	pendingShapePreset.value = preset
	pendingShapeType.value = shapeType
}

const makeIcon = (children) => (_, { attrs }) =>
	h(
		'svg',
		{
			xmlns: 'http://www.w3.org/2000/svg',
			fill: 'none',
			viewBox: '0 0 24 24',
			stroke: 'currentColor',
			...attrs,
			class: ['stroke-[1.5]', attrs.class],
		},
		children,
	)

export const shapeTools = [
	{
		label: __('Rectangle'),
		icon: makeIcon([h('rect', { x: '2', y: '5', width: '20', height: '14' })]),
		onClick: () => armTool('rectangle'),
	},
	{
		label: __('Oval'),
		icon: makeIcon([h('ellipse', { cx: '12', cy: '12', rx: '10', ry: '7' })]),
		onClick: () => armTool('oval'),
	},
	{
		label: __('Diamond'),
		icon: makeIcon([h('polygon', { points: '12,2 22,12 12,22 2,12' })]),
		onClick: () => armTool('diamond'),
	},
	{
		label: __('Triangle'),
		icon: makeIcon([h('polygon', { points: '12,2 22,21 2,21' })]),
		onClick: () => armTool('triangle'),
	},
	{
		label: __('Pentagon'),
		icon: makeIcon([h('polygon', { points: '12,2 21.5,8.9 17.9,20.1 6.1,20.1 2.5,8.9' })]),
		onClick: () => armTool('pentagon'),
	},
	// One: the star and the block arrow, utils/shapeGeometry.js; VENDORED.md
	{
		label: __('Star'),
		icon: makeIcon([h('polygon', { points: '12,2 14.4,8.8 21.5,8.9 15.8,13.2 17.9,20.1 12,16 6.1,20.1 8.2,13.2 2.5,8.9 9.6,8.8' })]),
		onClick: () => armTool('star'),
	},
	{
		label: __('Block Arrow'),
		icon: makeIcon([h('polygon', { points: '2,9 14,9 14,4 22,12 14,20 14,15 2,15' })]),
		onClick: () => armTool('blockArrow'),
	},
]

const round = { 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }

export const lineTools = [
	{
		label: __('Line'),
		icon: makeIcon([h('line', { x1: '3', y1: '12', x2: '21', y2: '12', ...round })]),
		onClick: () => armTool('line', { markerStart: 'none', markerEnd: 'none' }),
	},
	{
		label: __('Arrow'),
		icon: makeIcon([h('path', { d: 'M3 12h18M15 6l6 6-6 6', ...round })]),
		onClick: () => armTool('line', { markerStart: 'none', markerEnd: 'arrow' }),
	},
	{
		label: __('Double arrow'),
		icon: makeIcon([h('path', { d: 'M3 12h18M9 6l-6 6 6 6M15 6l6 6-6 6', ...round })]),
		onClick: () => armTool('line', { markerStart: 'arrow', markerEnd: 'arrow' }),
	},
	{
		label: __('Connector'),
		icon: makeIcon([
			h('rect', { x: '2', y: '3', width: '7', height: '7' }),
			h('rect', { x: '15', y: '14', width: '7', height: '7' }),
			h('line', { x1: '9', y1: '10', x2: '15', y2: '14' }),
		]),
		onClick: () => armTool('connector', { route: 'straight' }),
	},
	{
		label: __('Elbow connector'),
		icon: makeIcon([
			h('rect', { x: '2', y: '3', width: '7', height: '7' }),
			h('rect', { x: '15', y: '14', width: '7', height: '7' }),
			h('path', { d: 'M9 6.5h3.5v11H15' }),
		]),
		onClick: () => armTool('connector', { route: 'elbow' }),
	},
]
