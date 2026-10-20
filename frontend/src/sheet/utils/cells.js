// Derived from frappe/suite@df7f341 (frontend/src/apps/sheets)/utils/cells.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
export function colLabel(idx) {
  let s = ''; idx++
  while (idx > 0) { s = String.fromCharCode(64 + (idx % 26 || 26)) + s; idx = Math.floor((idx - 1) / 26) }
  return s
}

export function cellId(row, col) { return colLabel(col) + (row + 1) }

export function parseCellId(id) {
  const m = id.match(/^([A-Z]+)(\d+)$/)
  if (!m) return null
  return { row: parseInt(m[2]) - 1, col: m[1].split('').reduce((a, c) => a * 26 + c.charCodeAt(0) - 64, 0) - 1 }
}
