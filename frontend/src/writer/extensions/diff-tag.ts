// Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/extensions/diff-tag.ts. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { Mark, mergeAttributes } from '@tiptap/core'

const DiffTag = Mark.create({
  name: 'diffTag',

  parseHTML() {
    return [{ tag: 'ins', attrs: { type: 'insert' } }]
  },

  renderHTML({ node, HTMLAttributes }) {
    return ['ins', mergeAttributes(HTMLAttributes), 0]
  },
})

export default DiffTag
