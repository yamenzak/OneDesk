// Derived from frappe/suite@df7f341 (frontend/src/apps/sheets)/components/SheetEditor/toolbar.config.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
// Pure config factories for SheetEditor toolbar dropdowns.
// Each factory takes a map of action callbacks and returns a Frappe UI Dropdown options array.

import { __ } from '../../../kit/desk'

export function buildAlignOptions({ setAlign, setValign }) {
  return [
    { group: __('Horizontal'), options: [
      { label: __('Left'),   icon: 'lucide-align-left',   onClick: () => setAlign('left')   },
      { label: __('Center'), icon: 'lucide-align-center', onClick: () => setAlign('center') },
      { label: __('Right'),  icon: 'lucide-align-right',  onClick: () => setAlign('right')  },
    ]},
    { group: __('Vertical'), options: [
      { label: __('Top'),    icon: 'lucide-arrow-up',   onClick: () => setValign('top')    },
      { label: __('Middle'), icon: 'lucide-minus', onClick: () => setValign('middle') },
      { label: __('Bottom'), icon: 'lucide-arrow-down', onClick: () => setValign('bottom') },
    ]},
  ]
}

export function buildBorderOptions({ applyBorder }) {
  return [
    { group: __('Apply to selection'), options: [
      { label: __('All borders'),     icon: 'lucide-grid-2x2', onClick: () => applyBorder('all')     },
      { label: __('Outside borders'), icon: 'lucide-square',   onClick: () => applyBorder('outside') },
      { label: __('Inner borders'),   icon: 'lucide-plus',     onClick: () => applyBorder('inner')   },
    ]},
    { group: __('Single side'), options: [
      { label: __('Top border'),    icon: 'lucide-arrow-up',    onClick: () => applyBorder('top')    },
      { label: __('Bottom border'), icon: 'lucide-arrow-down',  onClick: () => applyBorder('bottom') },
      { label: __('Left border'),   icon: 'lucide-arrow-left',  onClick: () => applyBorder('left')   },
      { label: __('Right border'),  icon: 'lucide-arrow-right', onClick: () => applyBorder('right')  },
    ]},
    { group: __('Remove'), options: [
      { label: __('No border'), icon: 'lucide-square-x', theme: 'red', onClick: () => applyBorder('none') },
    ]},
  ]
}

/**
 * The "…" overflow menu.
 *
 * `collapsed` mirrors the toolbar's `max-width: 1280px` breakpoint. An option
 * marked `inline: true` also has its own toolbar button, and that button is
 * only rendered above the breakpoint — so an uncollapsed toolbar drops those
 * options from the menu instead of listing them twice. Options left unmarked
 * have no toolbar button at any width; they must stay in the menu or they
 * become unreachable with the mouse.
 */
export function buildMoreToolbarOptions({
  toggleFmt, toggleWrap, toggleFormatPainter, clearFormatting,
  adjustDecimals, openCfDialog, openHyperlinkDialog, toggleMerge,
  toggleSortFilter, applyBorder, zoomBy, resetZoom, openPivotDialog,
  openChartDialog, openNamedRangesDialog, runSmartFill,
  collapsed = true,
}) {
  const groups = [
    { group: __('Format'), options: [
      { label: __('Strikethrough'),    icon: 'lucide-strikethrough',    inline: true, onClick: () => toggleFmt('strikethrough') },
      { label: __('Wrap text'),        icon: 'lucide-corner-down-left', inline: true, onClick: () => toggleWrap()              },
      { label: __('Format painter'),   icon: 'lucide-paint-roller',     inline: true, onClick: () => toggleFormatPainter()     },
      { label: __('Clear formatting'), icon: 'lucide-eraser',           inline: true, onClick: () => clearFormatting()         },
    ]},
    { group: __('Numbers'), options: [
      { label: __('Decrease decimal places'), icon: 'lucide-minus', inline: true, onClick: () => adjustDecimals(-1) },
      { label: __('Increase decimal places'), icon: 'lucide-plus',  inline: true, onClick: () => adjustDecimals(+1) },
    ]},
    { group: __('Cells'), options: [
      { label: __('Conditional formatting'), icon: 'lucide-blend',      inline: true, onClick: () => openCfDialog(null)    },
      { label: __('Insert hyperlink'),       icon: 'lucide-link',       inline: true, onClick: () => openHyperlinkDialog() },
      { label: __('Merge / unmerge'),        icon: 'lucide-maximize-2', inline: true, onClick: () => toggleMerge()         },
      { label: __('Toggle filter'),          icon: 'lucide-filter',     inline: true, onClick: () => toggleSortFilter()    },
      { label: __('Smart Fill ({0})', ['Ctrl+E']), icon: 'lucide-zap',                      onClick: () => runSmartFill?.()      },
    ]},
    { group: __('Borders'), options: [
      { label: __('All borders'),     icon: 'lucide-grid-2x2', inline: true, onClick: () => applyBorder('all')     },
      { label: __('Outside borders'), icon: 'lucide-square',   inline: true, onClick: () => applyBorder('outside') },
      { label: __('No border'),       icon: 'lucide-square-x', inline: true, onClick: () => applyBorder('none')    },
    ]},
    { group: __('View'), options: [
      { label: __('Zoom in'),    icon: 'lucide-zoom-in',  onClick: () => zoomBy(+0.1)  },
      { label: __('Zoom out'),   icon: 'lucide-zoom-out', onClick: () => zoomBy(-0.1)  },
      { label: __('Reset zoom'), icon: 'lucide-minimize', onClick: () => resetZoom()   },
    ]},
    { group: __('Insert'), options: [
      { label: __('Pivot table…'), icon: 'lucide-layout',                  onClick: () => openPivotDialog() },
      { label: __('Chart…'),       icon: 'lucide-chart-bar', inline: true, onClick: () => openChartDialog() },
    ]},
    { group: __('Workbook'), options: [
      { label: __('Named ranges…'), icon: 'lucide-bookmark', onClick: () => openNamedRangesDialog() },
    ]},
  ]

  if (collapsed) return groups
  return groups
    .map((g) => ({ ...g, options: g.options.filter((o) => !o.inline) }))
    .filter((g) => g.options.length > 0)
}
