// Derived from frappe/suite@df7f341 (frontend/src/apps/sheets)/engine/sheet.test.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { describe, it, expect, beforeEach } from 'vitest'
import { createSheet } from './sheet.js'
import { adjustFormula } from './formula-adjust.js'

describe('row / column shifting', () => {
  let sheet
  beforeEach(() => { sheet = createSheet() })

  function column() {
    // Materialise column A as { row(1-indexed): value } for terse assertions.
    const data = sheet.getRawData()
    const out = {}
    for (const id in data) {
      const m = id.match(/^A(\d+)$/)
      if (m) out[m[1]] = data[id]?.value ?? data[id]
    }
    return out
  }

  it('deleteRow keeps every row below the deleted one (regression)', () => {
    // Deleting a single row used to destroy all rows below it: _shiftCells
    // moved rows up in descending order, so each cell landed on a slot a
    // not-yet-processed cell still held, and the next delete wiped it.
    ;['r1', 'r2', 'r3', 'r4', 'r5'].forEach((v, i) => sheet.setCell('A' + (i + 1), v))
    sheet.deleteRow(1)                   // remove row 2 (r2), rest shift up
    expect(column()).toEqual({ 1: 'r1', 2: 'r3', 3: 'r4', 4: 'r5' })
  })

  it('deleteRow rewrites formula-bearing cells without loss', () => {
    sheet.setCell('A1', '10')
    sheet.setCell('A2', '20')
    sheet.setCell('A3', '=A1+A2')        // 30
    sheet.setCell('A4', 'tail')
    sheet.deleteRow(1)                   // drop A2; A3→A2, A4→A3
    expect(column()).toEqual({ 1: '10', 2: '=A1+A2', 3: 'tail' })
  })

  it('insertRow still pushes rows down without loss', () => {
    ;['r1', 'r2', 'r3'].forEach((v, i) => sheet.setCell('A' + (i + 1), v))
    sheet.insertRow(1)                   // open a gap at row 2
    expect(column()).toEqual({ 1: 'r1', 3: 'r2', 4: 'r3' })
  })
})

// One: a reference may carry `$` anywhere Excel writes it. A leading `$` was
// dropped, so `$A1` worked by accident while `$A$1` and `A$1` were #NAME? and
// `SUM($A$1:$A$3)` answered 0.
describe('$ references', () => {
  let sheet
  beforeEach(() => {
    sheet = createSheet()
    sheet.setCell('A1', '2'); sheet.setCell('A2', '3'); sheet.setCell('A3', '4'); sheet.setCell('B1', '10')
  })
  const read = (formula) => { sheet.setCell('C1', formula); return sheet.getCellValue('C1') }

  it('read wherever the $ is', () => {
    for (const f of ['=$A$1', '=A$1', '=$A1', '=$a$1', '=Sheet1!$A$1']) expect(read(f)).toBe(2)
    expect(read('=$A$1*B1')).toBe(20)
    expect(read('=IF($A$1>1,"y","n")')).toBe('y')
  })

  it('in ranges and whole columns', () => {
    expect(read('=SUM($A$1:$A$3)')).toBe(9)
    expect(read('=SUM(A$1:$A3)')).toBe(9)
    expect(read('=SUM($A:$A)')).toBe(9)
    expect(read('=COUNT($A1:A$3)')).toBe(3)
  })

  it('recalculated when what it names changes', () => {
    sheet.setCell('C2', '=$A$1*2')
    sheet.setCell('A1', '5')
    expect(sheet.getCellValue('C2')).toBe(10)
  })

  it('kept where it is when filled down', () => {
    expect(adjustFormula('=$A$1*B1', 1, 0)).toBe('=$A$1*B2')
    expect(adjustFormula('=A$1+$B2', 2, 1)).toBe('=B$1+$B4')
  })
})
