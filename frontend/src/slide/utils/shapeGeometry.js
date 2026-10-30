// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/utils/shapeGeometry.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
const POLYGON_SIDES = { diamond: 4, triangle: 3, pentagon: 5 }

// One: a star and a block arrow, drawn on a unit box rather than as regular polygons; VENDORED.md
const STAR = Array.from({ length: 10 }, (_, k) => {
	const angle = -Math.PI / 2 + (k * Math.PI) / 5
	const radius = k % 2 ? 0.4 : 1
	return { x: radius * Math.cos(angle), y: radius * Math.sin(angle) }
})
const BLOCK_ARROW = [
	{ x: 0, y: 0.3 }, { x: 0.6, y: 0.3 }, { x: 0.6, y: 0 }, { x: 1, y: 0.5 },
	{ x: 0.6, y: 1 }, { x: 0.6, y: 0.7 }, { x: 0, y: 0.7 },
]
const DRAWN = { star: STAR, blockArrow: BLOCK_ARROW }

export const isPolygonShape = (shapeType) => shapeType in POLYGON_SIDES || shapeType in DRAWN

// regular polygon filling width × height from the top, inset by half the stroke
export const getPolygonVertices = (shapeType, width, height, strokeInset = 0) => {
	const sides = POLYGON_SIDES[shapeType]
	if (!sides && !DRAWN[shapeType]) return []

	const unitVertices =
		DRAWN[shapeType] ||
		Array.from({ length: sides }, (_, k) => {
			const angle = -Math.PI / 2 + (k * 2 * Math.PI) / sides
			return { x: Math.cos(angle), y: Math.sin(angle) }
		})

	const xMin = Math.min(...unitVertices.map((v) => v.x))
	const xMax = Math.max(...unitVertices.map((v) => v.x))
	const yMin = Math.min(...unitVertices.map((v) => v.y))
	const yMax = Math.max(...unitVertices.map((v) => v.y))

	const scaleX = (x) => strokeInset + ((x - xMin) / (xMax - xMin)) * (width - 2 * strokeInset)
	const scaleY = (y) => strokeInset + ((y - yMin) / (yMax - yMin)) * (height - 2 * strokeInset)

	return unitVertices.map((v) => ({ x: scaleX(v.x), y: scaleY(v.y) }))
}

// the top shifts with the stroke so the visible line stays put
export const setStrokeWidthInPlace = (element, value) => {
	if (element.shapeType === 'line' && !element.points) {
		element.top += (element.strokeWidth - value) / 2
		element.height = value
	}
	element.strokeWidth = value
}
