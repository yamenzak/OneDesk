// Derived from frappe/suite@df7f341 (frontend/src/apps/sheets)/components/SheetEditor/useShortcuts.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { useKeyboardShortcut } from 'frappe-ui'
import { __ } from '../../../kit/desk'

/**
 * Keyboard shortcut dispatch for SheetEditor.
 *
 * App-level shortcuts are registered through frappe-ui's `useShortcut` registry
 * so they are the single source of truth for the `<KeyboardShortcutsModal>` — the
 * shortcut description lives next to its handler, so the help dialog can never
 * drift. Grid navigation/edit shortcuts stay in the canvas (they need the canvas
 * element + edit-mode state); they're registered here as *display-only* entries
 * (no handler, `preventDefault: false`) purely so the modal lists them too.
 *
 * A small residual `onGlobalKey` handles the shortcuts frappe-ui's `e.key`
 * matcher cannot: the context-sensitive Escape cascade, and the `e.code`-based
 * combos (macOS rewrites Alt+= → ≠ and Shift+<digit> → a symbol).
 *
 * @param {{
 *   formulaInputEl: () => HTMLElement | null,
 *   undo: () => void, redo: () => void, onSave: () => void,
 *   toggleFmt: (fmt: string) => void, repeatLast: () => void,
 *   toggleShowFormulas: () => void,
 *   showFindReplace: import('vue').Ref<boolean>,
 *   openVersionHistory: () => void, openHyperlinkDialog: () => void,
 *   openCommentPanel: () => void, openQuickFilterForActive: () => void,
 *   zoomBy: (d: number) => void, resetZoom: () => void,
 *   commentPanel: { open: boolean },
 *   dropdownPanel: { open: boolean },
 *   splitText: { open: boolean },
 *   revertSplitPreview: () => void, closeSplit: () => void,
 *   clipboard: { hasData: () => boolean, clear: () => void },
 *   clipboardHas: import('vue').Ref<boolean>,
 *   setMarchingAnts: (v: null) => void,
 *   fillDown: () => void, fillRight: () => void,
 *   runSmartFill: () => void,
 *   insertRowsCols: () => void, deleteRowsCols: () => void,
 *   applyNumberFormat: (fmt: string) => void, pasteValues: () => void,
 *   readOnly?: () => boolean,
 * }} actions
 */

// Ctrl/Cmd+Shift+<digit> → number-format key, matching Google Sheets' 1-6 row.
// Keyed by KeyboardEvent.code so shifted digits ('!', '@', …) still resolve.
// Exponent/scientific (GS's Ctrl+Shift+6) is intentionally absent — the format
// engine has no scientific renderer yet, so there's nothing correct to apply.
const NUMBER_FORMAT_KEYS = {
  Digit1: 'number',
  Digit2: 'time',
  Digit3: 'date',
  Digit4: 'currency:USD:2',
  Digit5: 'percentage',
}

export function useShortcuts(actions) {
  const {
    formulaInputEl, undo, redo, onSave, toggleFmt, repeatLast,
    toggleShowFormulas, showFindReplace, openFindReplace,
    openVersionHistory, openHyperlinkDialog, openCommentPanel, openQuickFilterForActive,
    zoomBy, resetZoom,
    commentPanel, dropdownPanel, splitText, revertSplitPreview, closeSplit,
    clipboard, clipboardHas, setMarchingAnts,
    fillDown, fillRight,
    runSmartFill,
    insertRowsCols, deleteRowsCols, applyNumberFormat, pasteValues,
    // Optional getter — true for a view-only viewer (guest / read-only share).
    // Mutating shortcuts carry `enabled: notReadOnly` so they're both inert
    // AND hidden from the modal while read-only; pure view shortcuts stay live.
    readOnly = () => false,
  } = actions

  const notReadOnly = () => !readOnly()

  function _isInInput() {
    const ae = document.activeElement
    return ae?.tagName === 'INPUT' && ae !== formulaInputEl?.()
  }

  // ── Registry (source of truth for the modal) ─────────────────────────────────
  // Shortcuts frappe-ui can match on `e.key`, registered with handler + label.
  useKeyboardShortcut([
    // View / tools — available even in read-only.
    { combo: 'Mod+S',  description: __('Save'),            group: __('View'), handler: onSave },
    {
      combo: 'Mod+F',
      description: __('Find & replace'),
      group: __('View'),
      allowInInput: true,
      handler: () => {
        document.activeElement?.blur?.()
        if (openFindReplace) openFindReplace()
        else if (showFindReplace) showFindReplace.value = true
      },
    },
    { combo: 'Mod+Backtick', description: __('Show formulas'), group: __('View'), handler: toggleShowFormulas },
    { combo: 'Mod+Equal', description: __('Zoom in'), group: __('View'), handler: () => zoomBy(+0.1) },
    { combo: 'Mod+Shift+Equal', description: __('Zoom in'), group: __('View'), handler: () => zoomBy(+0.1) },
    { combo: 'Mod+Minus', description: __('Zoom out'), group: __('View'), handler: () => zoomBy(-0.1) },
    { combo: 'Mod+Digit0',  description: __('Reset zoom'),      group: __('View'), handler: resetZoom },

    // Editing — mutating, so hidden + inert while read-only.
    { combo: 'Mod+Z', description: __('Undo'),                    group: __('Editing'), enabled: notReadOnly, handler: undo },
    { combo: 'Mod+Shift+Z', description: __('Redo'),                    group: __('Editing'), enabled: notReadOnly, handler: redo },
    { combo: 'Mod+Y', description: __('Redo'),                    group: __('Editing'), enabled: notReadOnly, handler: redo },
    { combo: 'F4',                         description: __('Repeat last action'),      group: __('Editing'), enabled: notReadOnly, handler: repeatLast },
    { combo: 'Mod+D', description: __('Fill down'),               group: __('Editing'), enabled: notReadOnly, handler: fillDown },
    { combo: 'Mod+R', description: __('Fill right'),              group: __('Editing'), enabled: notReadOnly, handler: fillRight },
    { combo: 'Mod+E', description: __('Smart Fill from examples'), group: __('Editing'), enabled: notReadOnly, handler: () => runSmartFill?.() },
    { combo: 'Mod+Shift+V', description: __('Paste values only'),       group: __('Editing'), enabled: notReadOnly, handler: () => pasteValues?.() },
    { combo: 'Mod+L', description: __('Insert hyperlink'),        group: __('Editing'), enabled: notReadOnly, handler: openHyperlinkDialog },
    { combo: 'Shift+F2', description: __('Add / edit comment'),      group: __('Editing'), enabled: notReadOnly, handler: openCommentPanel },
    { combo: 'Alt+ArrowDown', description: __('Quick filter on column'),  group: __('Editing'), enabled: notReadOnly, handler: openQuickFilterForActive },
    { combo: 'Mod+Alt+Shift+H', description: __('Version history'), group: __('Editing'), enabled: notReadOnly, handler: openVersionHistory },

    // Formatting — mutating.
    { combo: 'Mod+B', description: __('Bold'),          group: __('Formatting'), enabled: notReadOnly, handler: () => toggleFmt('bold') },
    { combo: 'Mod+I', description: __('Italic'),        group: __('Formatting'), enabled: notReadOnly, handler: () => toggleFmt('italic') },
    { combo: 'Mod+U', description: __('Underline'),     group: __('Formatting'), enabled: notReadOnly, handler: () => toggleFmt('underline') },
    { combo: 'Mod+Shift+X', description: __('Strikethrough'), group: __('Formatting'), enabled: notReadOnly, handler: () => toggleFmt('strikethrough') },
  ])

  // ── Display-only entries ─────────────────────────────────────────────────────
  // Real handlers live in the grid canvas, the native clipboard events, or the
  // residual onGlobalKey below. `preventDefault: false` + no handler keeps them
  // passive — they never intercept a keystroke, they just populate the modal.
  useKeyboardShortcut([
    // Navigation (grid canvas)
    { combo: 'ArrowUp',    description: __('Move selection'), group: __('Navigation'), preventDefault: false },
    { combo: 'ArrowDown',  description: __('Move selection'), group: __('Navigation'), preventDefault: false },
    { combo: 'ArrowLeft',  description: __('Move selection'), group: __('Navigation'), preventDefault: false },
    { combo: 'ArrowRight', description: __('Move selection'), group: __('Navigation'), preventDefault: false },
    { combo: 'Shift+ArrowRight', description: __('Extend selection'),       group: __('Navigation'), preventDefault: false },
    { combo: 'Mod+ArrowLeft',  description: __('Jump to data-region edge'), group: __('Navigation'), preventDefault: false },
    { combo: 'Mod+Home',       description: __('Jump to start / end'),    group: __('Navigation'), preventDefault: false },
    { combo: 'Mod+End',        description: __('Jump to start / end'),    group: __('Navigation'), preventDefault: false },
    { combo: 'PageDown',   description: __('Scroll one screen'), group: __('Navigation'), preventDefault: false },
    { combo: 'PageUp',     description: __('Scroll one screen'), group: __('Navigation'), preventDefault: false },

    // Selection (grid canvas)
    { combo: 'Shift+Space', description: __('Select row'),          group: __('Selection'), preventDefault: false },
    { combo: 'Mod+Space', description: __('Select column'),       group: __('Selection'), preventDefault: false },
    { combo: 'Mod+A', description: __('Select data / all'),   group: __('Selection'), preventDefault: false },
    { combo: 'Mod+Shift+Space', description: __('Select entire sheet'), group: __('Selection'), preventDefault: false },

    // Editing (grid canvas / native clipboard / residual handler)
    { combo: 'F2',                         description: __('Edit cell'),            group: __('Editing'), preventDefault: false },
    { combo: 'Delete',                     description: __('Clear cell'),           group: __('Editing'), preventDefault: false },
    { combo: 'Backspace',                  description: __('Clear cell'),           group: __('Editing'), preventDefault: false },
    { combo: 'Enter',                      description: __('Edit cell / commit + move down'), group: __('Editing'), preventDefault: false },
    { combo: 'Tab',                        description: __('Commit + move right'),  group: __('Editing'), preventDefault: false },
    { combo: 'Alt+Enter', description: __('New line in cell'),     group: __('Editing'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+C', description: __('Copy'),                 group: __('Editing'), preventDefault: false },
    { combo: 'Mod+X', description: __('Cut'),                  group: __('Editing'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+V', description: __('Paste'),                group: __('Editing'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+Alt+Equal', description: __('Insert rows / columns'), group: __('Editing'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+Alt+Minus', description: __('Delete rows / columns'), group: __('Editing'), enabled: notReadOnly, preventDefault: false },

    // Number formats (Ctrl+Shift+1..5) — handled via e.code below; here for display.
    { combo: 'Mod+Shift+Digit1', description: __('Format as number'),   group: __('Formatting'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+Shift+Digit2', description: __('Format as time'),     group: __('Formatting'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+Shift+Digit3', description: __('Format as date'),     group: __('Formatting'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+Shift+Digit4', description: __('Format as currency'), group: __('Formatting'), enabled: notReadOnly, preventDefault: false },
    { combo: 'Mod+Shift+Digit5', description: __('Format as percent'),  group: __('Formatting'), enabled: notReadOnly, preventDefault: false },
  ])

  // ── Residual handler (window keydown) ────────────────────────────────────────
  // Everything frappe-ui's e.key matcher can't do: the Escape cascade and the
  // e.code-based combos.
  function onGlobalKey(e) {
    const inInput = _isInInput()

    // Escape — context-sensitive close (first match wins). Kept custom because
    // it's a cascade, not a single action; while editing a cell the canvas owns
    // Escape (cancel edit) and focus is in the editor, so inInput short-circuits.
    if (e.key === 'Escape' && !inInput) {
      if (commentPanel.open)   { commentPanel.open  = false; return }
      if (dropdownPanel.open)  { dropdownPanel.open = false; return }
      if (splitText.open)      { revertSplitPreview(); closeSplit(); return }
      if (clipboard.hasData()) { clipboard.clear(); clipboardHas.value = false; setMarchingAnts(null); return }
      return
    }

    if (readOnly() || inInput) return
    const mod = e.metaKey || e.ctrlKey

    // Mod+Alt+= / Mod+Alt+-  — insert / delete rows or columns. Match on e.code:
    // with Alt held, macOS rewrites e.key ('=' → '≠', '-' → '–').
    if (mod && e.altKey && e.code === 'Equal') { e.preventDefault(); insertRowsCols?.(); return }
    if (mod && e.altKey && e.code === 'Minus') { e.preventDefault(); deleteRowsCols?.(); return }
    // Mod+Shift+1..5 — number formats. Match on e.code so shifted digits resolve.
    if (mod && e.shiftKey && NUMBER_FORMAT_KEYS[e.code]) {
      e.preventDefault(); applyNumberFormat?.(NUMBER_FORMAT_KEYS[e.code]); return
    }
  }

  return { onGlobalKey }
}
