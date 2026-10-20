// What FIELD(doctype, name, field) reads: another record's fields, asked for
// together a moment after the formulas first name them (one_sheet/api.py,
// records) and kept while the workbook is open. A record not there yet reads
// as blank; when it comes, whoever listens draws again.
import { call } from '../utils/api.js'

const held = new Map()
const wanted = new Set()
const listeners = new Set()
let timer = null

const keyOf = (doctype, name) => `${doctype}\u0000${name}`

export function field(doctype, name, fieldname) {
	if (!doctype || !name) return ''
	const key = keyOf(doctype, name)
	if (!held.has(key)) {
		held.set(key, null)
		wanted.add(key)
		clearTimeout(timer)
		timer = setTimeout(fetch, 40)
	}
	return held.get(key)?.[fieldname] ?? ''
}

export function onFields(fn) {
	listeners.add(fn)
	return () => listeners.delete(fn)
}

// Asks again next time: a record changed, or the workbook is opened again.
export function forget() {
	held.clear()
}

async function fetch() {
	const keys = [...wanted]
	wanted.clear()
	if (!keys.length) return
	const asked = keys.map((key) => key.split('\u0000'))
	let got = {}
	try {
		got = (await call('onedesk.one_sheet.api.records', { asked: JSON.stringify(asked) })) || {}
	} catch {
		got = {}
	}
	for (const [doctype, name] of asked) held.set(keyOf(doctype, name), got[doctype]?.[name] || {})
	for (const fn of listeners) fn()
}
