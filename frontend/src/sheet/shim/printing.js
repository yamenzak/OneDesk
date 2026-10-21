// A sheet as one_sheet/paper.py draws it on paper: the text each cell shows,
// the format keys that print, merges, widths, heights and what is hidden.
// Never HTML; the page is written on the server.
import { parseCellId } from '../utils/cells.js'
import { applyNumberFmt } from '../utils/format-number.js'

const PRINTED = [
  'bold', 'italic', 'underline', 'strikethrough', 'color', 'backgroundColor',
  'fontSize', 'fontFamily', 'align', 'valign', 'textWrap', 'wrapText',
  'borderTop', 'borderBottom', 'borderLeft', 'borderRight',
]

const FILLED = ['backgroundColor', 'borderTop', 'borderBottom', 'borderLeft', 'borderRight']

function _kept(fmt) {
  const out = {}
  for (const key of PRINTED) if (fmt?.[key] != null && fmt[key] !== '' && fmt[key] !== false) out[key] = fmt[key]
  return out
}

// What one sheet prints: `view` is that sheet's entry in useSheetTabs'
// per-sheet view (colW, rowH, hiddenRows, hiddenCols, freezeRows).
export function printable({ sheet, formats, merge, condFormat, validation }, sn, view = {}) {
  const data = sheet.getRawData(sn)
  const styled = formats.snapshot()?.[sn]?.cells || {}
  const masters = merge.snapshot()?.[sn]?.masterMap || {}
  let rows = 0, cols = 0
  const reach = (r, c) => { if (r + 1 > rows) rows = r + 1; if (c + 1 > cols) cols = c + 1 }
  const ids = new Set(Object.keys(data))
  for (const [id, fmt] of Object.entries(styled)) if (FILLED.some((key) => fmt?.[key])) ids.add(id)
  for (const id of ids) { const p = parseCellId(id); if (p) reach(p.row, p.col) }
  for (const { r, c, rowSpan, colSpan } of Object.values(masters)) reach(r + rowSpan - 1, c + colSpan - 1)

  const cells = []
  for (const id of ids) {
    const p = parseCellId(id)
    if (!p) continue
    const fmt = formats.get(id, sn) || {}
    const value = sheet.getCellValue(id, sn)
    const shown = sheet.getDisplayValue(id, sn) ?? ''
    let text = fmt.numberFormat ? applyNumberFmt(shown, fmt.numberFormat) : shown
    if (validation?.get(id, sn)?.type === 'checkbox') text = String(value).toUpperCase() === 'TRUE' || value === true ? '✓' : ''
    const over = condFormat?.getFormatOverride(id, value, sn, (cid) => sheet.getDisplayValue(cid, sn)) || {}
    const look = _kept({ ...fmt, ...over })
    if (!look.align && typeof value === 'number') look.align = 'right'
    const image = value && value.__spark && value.image ? value.image : null
    if (value && value.__spark && !image) text = ''
    cells.push(image ? [p.row, p.col, '', look, image] : [p.row, p.col, String(text ?? ''), look])
  }

  const widths = {}
  for (let c = 0; c < cols; c++) if (view.colW?.[c] != null) widths[c] = Math.round(view.colW[c])
  const heights = {}
  for (const [r, h] of Object.entries(view.rowH || {})) if (+r < rows) heights[r] = Math.round(h)
  return {
    name: sn,
    size: [rows, cols],
    cells,
    merges: Object.values(masters).map(({ r, c, rowSpan, colSpan }) => [r, c, rowSpan, colSpan]),
    widths,
    heights,
    hidden_rows: (view.hiddenRows || []).filter((r) => r < rows),
    hidden_cols: (view.hiddenCols || []).filter((c) => c < cols),
    head: view.freezeRows || 0,
  }
}

