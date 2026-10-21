// What is wrong with a cell, as Excel and Google Sheets mark it: a formula
// that works out to an error, or a value the record refused (one_sheet/
// table.py, apply's `faults`). Pure but for the words.
import { __ } from '../../kit/desk'

const SAID = {
	'#VALUE!': () => __('The formula uses a value of the wrong type, such as text where a number is expected.'),
	'#REF!': () => __('The formula refers to a cell or sheet that no longer exists.'),
	'#NAME?': () => __('The formula contains an unknown function or range name. Check the spelling.'),
	'#DIV/0!': () => __('The formula divides by zero or by an empty cell.'),
	'#N/A': () => __('The formula could not find the value it looks up.'),
	'#NUM!': () => __('The formula result is not a valid number.'),
	'#SPILL!': () => __('The formula results cannot be placed because a cell in the output range is not empty. Clear that cell.'),
	'#CIRCULAR!': () => __('The formula refers to its own cell, directly or through other cells.'),
	'#ERROR!': () => __('The formula has a syntax error. Check its brackets and commas.'),
	'#NULL!': () => __('The ranges in this formula do not intersect.'),
}

export function isError(value) {
	return typeof value === 'string' && Object.hasOwn(SAID, value)
}

// The problem a cell has: the record's word for it first, then a formula's
// error. { level: 'error' | 'warn', message, doctype?, value? } or null.
export function problemOf(id, value, faults) {
	const fault = faults?.[id]
	if (fault) return { level: fault.level || 'error', ...fault }
	if (isError(value)) return { level: 'error', message: SAID[value](), code: value }
	return null
}
