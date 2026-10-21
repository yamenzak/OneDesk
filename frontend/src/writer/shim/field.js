// A field block: where a document on a record shows one of the record's
// fields, as a print format's field does. In the editor it is a chip with
// the field's label; on paper one_doc/paper.py fills in the record's value,
// or a table of a child table's rows.
import { Node, mergeAttributes } from "@tiptap/core";

export const RecordField = Node.create({
	name: "recordField",
	group: "inline",
	inline: true,
	atom: true,
	selectable: true,

	addAttributes() {
		return {
			field: { default: "", parseHTML: (el) => el.getAttribute("data-field") || "", renderHTML: (attrs) => ({ "data-field": attrs.field }) },
			label: { default: "", parseHTML: (el) => el.textContent || "", renderHTML: () => ({}) },
		};
	},

	parseHTML() {
		return [{ tag: "span[data-field]", priority: 60 }];
	},

	renderHTML({ node, HTMLAttributes }) {
		return ["span", mergeAttributes(HTMLAttributes, { class: "rounded-2 bg-surface-gray-3 px-1 text-ink-gray-8" }), node.attrs.label || node.attrs.field];
	},

	renderText({ node }) {
		return `[${node.attrs.label || node.attrs.field}]`;
	},

	addCommands() {
		return {
			insertRecordField:
				(field, label) =>
				({ commands }) =>
					commands.insertContent([{ type: this.name, attrs: { field, label } }, { type: "text", text: " " }]),
		};
	},
});
