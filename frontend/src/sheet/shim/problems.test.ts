// One: what is wrong with a cell, the record's word first.
import { describe, it, expect } from 'vitest'
globalThis.window ??= {}
const { isError, problemOf } = await import('./problems.js')

describe('cell problems', () => {
  it('knows a formula’s error from a value', () => {
    expect([isError('#VALUE!'), isError('#SPILL!'), isError('#hashtag'), isError(12)]).toEqual([true, true, false, false])
  })
  it('puts what the record refused before a formula’s error', () => {
    const faults = { C3: { cell: 'C3', message: 'No Item called X.', doctype: 'Item', value: 'X' } }
    expect(problemOf('C3', '#REF!', faults)).toMatchObject({ level: 'error', doctype: 'Item', value: 'X' })
    expect(problemOf('D3', '#REF!', faults)).toMatchObject({ level: 'error', code: '#REF!' })
    expect(problemOf('D4', 'fine', faults)).toBeNull()
  })
})
