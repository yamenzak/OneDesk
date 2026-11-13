// The Builder half of a slide's looks: fades, blur and free CSS, read the same
// way here as by play.py and the screen's player. One's own; VENDORED.md.
import rules from '../../../../onedesk/one_deck/css.json'

const allowed = new Set(rules.properties)

// a free CSS box read declaration by declaration: what is kept, and what is not
export const readCss = (css) => {
	const kept = {}
	const dropped = []
	if (typeof css !== 'string') return { kept, dropped }
	if (css.length > rules.longest) return { kept, dropped: [css.slice(0, 20)] }
	for (const declaration of css.split(';')) {
		if (!declaration.trim()) continue
		const at = declaration.indexOf(':')
		const property = declaration.slice(0, at).trim().toLowerCase()
		const value = declaration.slice(at + 1).replace(/!important/gi, '').trim()
		const lower = value.toLowerCase()
		const fits =
			at > 0 &&
			allowed.has(property) &&
			value &&
			value.length <= rules.longestValue &&
			!rules.refused.some((word) => lower.includes(word))
		if (fits) kept[property] = value
		else dropped.push(property || declaration.trim())
	}
	return { kept, dropped }
}

export const cssOf = (css) => readCss(css).kept

// what an element's blur and free CSS add to its box
export const looksOf = (element) => {
	const style = cssOf(element?.css)
	const blur = Math.min(Number(element?.blur) || 0, rules.mostBlur)
	if (blur > 0) style.filter = [style.filter, `blur(${blur}px)`].filter(Boolean).join(' ')
	if (element?.hidden) style.visibility = 'hidden'
	return style
}

const FADE = /^linear-gradient\((-?\d+)deg, ([^,]+), ([^,]+)\)$/

// a slide's background is a colour or a two-colour fade
export const fadeOf = (background) => {
	const found = FADE.exec(background || '')
	return found ? { from: found[2], to: found[3], angle: Number(found[1]) } : null
}

export const fadeText = ({ from, to, angle }) => `linear-gradient(${Math.round(angle) || 0}deg, ${from}, ${to})`

// the two ends of a fade across a w × h box at an angle, for an SVG gradient
export const fadeEnds = (angle) => {
	const radians = ((Number(angle) || 0) - 90) * (Math.PI / 180)
	const x = Math.cos(radians) / 2
	const y = Math.sin(radians) / 2
	return { x1: 0.5 - x, y1: 0.5 - y, x2: 0.5 + x, y2: 0.5 + y }
}

// where a new fade goes: the colour it starts from, lighter if dark and darker if light
export const fadePartner = (colour) => {
	const hex = /^#([0-9a-f]{6})/i.exec(colour || '')
	if (!hex) return 'transparent'
	const parts = [0, 2, 4].map((at) => parseInt(hex[1].slice(at, at + 2), 16))
	const light = parts[0] * 0.3 + parts[1] * 0.59 + parts[2] * 0.11 > 128
	const toward = light ? 0 : 255
	return `#${parts.map((part) => Math.round(part + (toward - part) * 0.45).toString(16).padStart(2, '0')).join('')}`
}
