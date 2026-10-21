// Derived from frappe/suite@df7f341 (frontend/src/apps/writer)/extensions/tab-trailing-node.js. Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0; see VENDORED.md.
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'

const TabTrailingNode = Extension.create({
  name: 'tabTrailingNode',

  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: new PluginKey('tabTrailingNode'),
        appendTransaction(transactions, oldState, newState) {
          const { doc, tr, schema } = newState
          let modified = false

          doc.forEach((node, offset) => {
            if (node.type.name === 'tab') {
              const lastChild = node.lastChild
              if (lastChild.type === schema.nodes.table) {
                const endPos = offset + node.nodeSize - 1
                tr.insert(endPos, schema.nodes.paragraph.create())
                modified = true
              }
            }
          })

          return modified ? tr : null
        },
      }),
    ]
  },
})

export default TabTrailingNode