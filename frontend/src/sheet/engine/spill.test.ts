// One: a formula that works out to a range fills the cells below it.
import { describe, it, expect, beforeEach } from 'vitest'
import { createSheet } from './sheet.js'

describe('spill', () => {
  let sheet
  const column = (col, from, to, name = 'Items') =>
    Array.from({ length: to - from + 1 }, (_, i) => sheet.getDisplayValue(`${col}${from + i}`, name))

  beforeEach(() => {
    sheet = createSheet()
    sheet.addSheet('Costing')
    sheet.addSheet('Items')
    const cells = { A4: 'CW01', B4: 'Wall', C4: '10', A5: 'CW02', B5: 'Door', C5: '2', A6: 'CW03', B6: 'Glass', C6: '4' }
    for (const [id, v] of Object.entries(cells)) sheet.setCell(id, v, 'Costing')
  })

  it('fills a column from another sheet, to its last line', () => {
    sheet.setCell('A2', '=Costing!A4:A', 'Items')
    expect(column('A', 2, 5)).toEqual(['CW01', 'CW02', 'CW03', ''])
  })

  it('works a range cell by cell', () => {
    sheet.setCell('B2', '=Costing!C4:C*2', 'Items')
    sheet.setCell('C2', '=IF(Costing!A4:A="","",Costing!B4:B&"!")', 'Items')
    expect(column('B', 2, 4)).toEqual(['20', '4', '8'])
    expect(column('C', 2, 4)).toEqual(['Wall!', 'Door!', 'Glass!'])
  })

  it('reads spilled cells in other formulas', () => {
    sheet.setCell('B2', '=Costing!C4:C*2', 'Items')
    sheet.setCell('E2', '=SUM(B2:B)', 'Items')
    sheet.setCell('E3', '=B4+1', 'Items')
    expect(sheet.getDisplayValue('E2', 'Items')).toBe('32')
    expect(sheet.getDisplayValue('E3', 'Items')).toBe('9')
  })

  it('grows with its source', () => {
    sheet.setCell('A2', '=Costing!A4:A', 'Items')
    expect(column('A', 2, 5)).toEqual(['CW01', 'CW02', 'CW03', ''])
    sheet.setCell('A7', 'CW04', 'Costing')
    expect(column('A', 2, 5)).toEqual(['CW01', 'CW02', 'CW03', 'CW04'])
  })

  it('shows #SPILL! when a cell in the way holds something', () => {
    sheet.setCell('A2', '=Costing!A4:A', 'Items')
    sheet.setCell('A3', 'x', 'Items')
    expect(column('A', 2, 4)).toEqual(['#SPILL!', 'x', ''])
    sheet.setCell('A3', '', 'Items')
    expect(column('A', 2, 4)).toEqual(['CW01', 'CW02', 'CW03'])
  })

  it('counts spilled lines in the extent', () => {
    sheet.setCell('A2', '=Costing!A4:A', 'Items')
    expect(sheet.getExtent('Items')).toEqual({ rows: 4, cols: 1 })
  })

  it('shows an empty cell it reads as blank', () => {
    sheet.setCell('A1', '=Costing!A9', 'Items')
    sheet.setCell('A2', '=Costing!A9+1', 'Items')
    expect(column('A', 1, 2)).toEqual(['', '1'])
  })

  it('reading an empty cell never leaves a neighbour at #CIRCULAR!', () => {
    const line = { F2: '=(D2*E2)/10000', H2: '=F2*G2', J2: '=U2', K2: '=J2*C2', L2: '=H2+J2', U2: '=(R2*24)+(S2*19)+T2' }
    for (const [id, v] of Object.entries(line)) sheet.setCell(id, v, 'Items')
    expect(['K2', 'L2', 'J2', 'U2'].map(id => sheet.getDisplayValue(id, 'Items'))).toEqual(['0', '0', '0', '0'])
  })

  it('a real circle still says so', () => {
    sheet.setCell('A1', '=B1', 'Items')
    sheet.setCell('B1', '=A1', 'Items')
    expect(sheet.getDisplayValue('A1', 'Items')).toBe('#CIRCULAR!')
  })
})
