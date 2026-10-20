// A record's table as the workbook's first sheet (one_sheet/table.py): what
// the save sends for it, and the cells the record sends back.
import { cellId, parseCellId } from "../utils/cells.js";

const MOST_LINES = 5000;
const MOST_COLUMNS = 60;

// The bound sheet's worked-out values, line by line, header first: the
// server never works a formula out, so the browser sends what each shows.
export function tableValues(sheet, bound) {
	const cells = sheet.getAllRaw()?.[bound.sheet];
	if (!cells) return null;
	let lines = 0;
	let columns = 0;
	for (const id of Object.keys(cells)) {
		const at = parseCellId(id);
		if (!at) continue;
		lines = Math.max(lines, at.row + 1);
		columns = Math.max(columns, at.col + 1);
	}
	const rows = [];
	for (let row = 0; row < Math.min(lines, MOST_LINES); row++) {
		const line = [];
		for (let col = 0; col < Math.min(columns, MOST_COLUMNS); col++) {
			line.push(sheet.getDisplayValue(cellId(row, col), bound.sheet));
		}
		rows.push(line);
	}
	return JSON.stringify({ sheet: bound.sheet, rows });
}

// Write what the record sent back (row ids, worked-out columns, the new
// mark) through the engine, so co-editors and the next save see it too.
export function takeBack(sheet, bound, cells) {
	const ids = Object.keys(cells || {});
	for (const id of ids) sheet.setCell(id, cells[id], bound.sheet);
	return ids.length;
}
