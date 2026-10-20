// A record's table as the workbook's first sheet (one_sheet/table.py): what
// the save sends for it, and the cells the record sends back.
import { cellId } from "../utils/cells.js";

const MOST_LINES = 5000;
const MOST_COLUMNS = 60;

// The bound sheet's worked-out values, line by line, header first: the
// server never works a formula out, so the browser sends what each shows,
// lines a formula spilled into included.
export function tableValues(sheet, bound) {
	if (!sheet.getAllRaw()?.[bound.sheet]) return null;
	const { rows: lines, cols: columns } = sheet.getExtent(bound.sheet);
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
// mark) through the engine, so co-editors and the next save see it too. A
// cell a formula fills is the formula's: writing there would block it.
export function takeBack(sheet, bound, cells) {
	const ids = Object.keys(cells || {}).filter((id) => {
		const raw = sheet.getCell(id, bound.sheet);
		return !(typeof raw === "string" && raw.startsWith("=")) && !sheet.isSpilled(id, bound.sheet);
	});
	for (const id of ids) sheet.setCell(id, cells[id], bound.sheet);
	return ids.length;
}
