// Derived from frappe/suite@2831a5d (frontend/src/apps/slides)/utils/bundledFonts.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
// Inter is in the app bundle, these aren't
const bundledFontFaces = [
	'400 16px Anton',
	'400 16px "Courier Prime"',
	'italic 400 16px "Courier Prime"',
	'700 16px "Courier Prime"',
	'italic 700 16px "Courier Prime"',
]

// one char per unicode-range subset
const subsetSample = 'AĀẠ'

export const loadBundledFonts = (): Promise<unknown> => {
	if (!document.fonts?.load) return Promise.resolve()
	return Promise.all(bundledFontFaces.map((face) => document.fonts.load(face, subsetSample)))
}
