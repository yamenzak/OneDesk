// What is wrong with a cell, as Excel and Google Sheets mark it: a formula
// that works out to an error, or a value the record refused (one_sheet/
// table.py, apply's `faults`). Pure but for the words.
import { __ } from '../../kit/desk'

const SAID = {
	'#VALUE!': () => __('A value in this formula is the wrong kind, such as text where a number was wanted.'),
	'#REF!': () => __('This formula points at a cell or sheet that isn’t there any more.'),
	'#NAME?': () => __('This formula uses a name the sheet doesn’t know. Check the spelling of the function or range.'),
	'#DIV/0!': () => __('This formula divides by zero, or by an empty cell.'),
	'#N/A': () => __('The value this formula looks for wasn’t found.'),
	'#NUM!': () => __('This formula works out to a number that can’t be shown.'),
	'#SPILL!': () => __('This formula fills the cells below it, and one of them already holds something. Clear it.'),
	'#CIRCULAR!': () => __('This formula reads itself, through the cells it reads.'),
	'#ERROR!': () => __('This formula can’t be read. Check its brackets and commas.'),
	'#NULL!': () => __('Two ranges in this formula don’t meet.'),
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
