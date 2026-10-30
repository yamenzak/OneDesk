<!-- The presentation's sources, and their fields to put on a slide (shim/data.js,
     one_slide/data.py): a field is put in as a chip, filled each time the slide
     is drawn as whoever is looking. One's own; VENDORED.md. -->
<template>
	<Dialog v-model:open="open" :title="__('Data from Records')" size="xl">
		<div class="flex max-h-96 flex-col gap-4 overflow-y-auto" @keydown.stop>
			<p class="text-base text-ink-gray-7">{{ __("Words from a record stay up to date: they are read again each time the slide is shown, and show only what the person looking may see.") }}</p>
			<p v-if="!sources.length" class="text-sm text-ink-gray-5">{{ __("No sources yet. Add the record this presentation is about, or a list of records.") }}</p>
			<div v-for="one in sources" :key="one.key" class="flex flex-col gap-2 rounded-3 border border-outline-gray-1 p-3">
				<div class="flex items-center gap-2">
					<span class="text-base font-medium text-ink-gray-8">{{ said(one) }}</span>
					<Badge :label="kinds[one.kind]" />
					<Button v-if="!readonly" class="ms-auto" size="sm" variant="ghost" icon="lucide-x" :aria-label="__('Remove')" @click="remove(one.key)" />
				</div>
				<p v-if="fieldsOf[one.key] && !fieldsOf[one.key].length" class="text-sm text-ink-gray-5">{{ __("You may not read these records, so their fields are not offered.") }}</p>
				<div v-if="fieldsOf[one.key]?.length" class="flex flex-wrap items-center gap-2">
					<Combobox trigger="button" size="sm" :model-value="null" :options="offered(one)" :placeholder="one.kind === 'list' ? __('Put In a Figure') : __('Put In a Field')" @update:model-value="(value) => value && put(chip(one.key, value))" />
					<Button v-if="one.kind === 'list'" size="sm" icon-left="lucide-table" :label="__('Put In as a Table')" @click="asTable(one)" />
				</div>
			</div>
			<div v-if="!readonly" class="flex gap-2">
				<Button icon-left="lucide-plus" :label="__('Add a Source')" @click="add" />
			</div>
		</div>
	</Dialog>
</template>

<script setup>
import { reactive, watch } from "vue";
import { Badge, Button, Combobox, Dialog } from "frappe-ui";
import { call, prompt } from "../../kit/desk";
import { addTableElement, addTextElement } from "../stores/element";
import { chip, saveSources, sources } from "./data.js";
import { __ } from "./words.js";

const open = defineModel({ type: Boolean, default: false });
const props = defineProps({ record: { type: Object, default: null }, readonly: Boolean });

const kinds = { this: __("This record"), record: __("A record"), linked: __("Linked"), list: __("A list") };
const NUMBERS = ["Currency", "Float", "Int", "Percent"];
const fieldsOf = reactive({});
let placed = false;

const doctypeOf = (one) => (one.kind === "this" && props.record ? props.record.doctype : one.doctype);

async function learn() {
	for (const one of sources.value) {
		const doctype = doctypeOf(one);
		if (doctype && !fieldsOf[one.key]) fieldsOf[one.key] = await call("onedesk.one_slide.data.fields", { doctype });
	}
}
watch([open, sources], () => open.value && learn(), { immediate: true });

const said = (one) => {
	const doctype = __(doctypeOf(one) || "");
	if (one.kind === "record") return `${doctype}: ${one.name}`;
	if (one.kind === "linked") return `${doctype} (${one.from}.${one.field})`;
	if (one.kind === "this") return props.record ? `${doctype}: ${props.record.name}` : doctype;
	return doctype;
};

// a record's fields, or a list's count and the total of each of its numbers
const offered = (one) =>
	one.kind === "list"
		? [{ label: __("Count"), value: "count" }, ...(fieldsOf[one.key] || []).filter((field) => NUMBERS.includes(field.fieldtype)).map((field) => ({ label: __("Total of {0}", [field.label]), value: `sum.${field.fieldname}` }))]
		: (fieldsOf[one.key] || []).map((field) => ({ label: field.label, value: field.fieldname }));

const keyFor = (doctype) => {
	const base = (doctype || "data").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").replace(/^(\d)/, "x$1").slice(0, 24) || "data";
	let key = base;
	for (let n = 2; sources.value.some((one) => one.key === key); n++) key = `${base}_${n}`;
	return key;
};

// the link fields of every record source, as where a linked source is reached from
const linksFrom = () =>
	sources.value
		.filter((one) => one.kind !== "list")
		.flatMap((one) => (fieldsOf[one.key] || []).filter((field) => field.options).map((field) => ({ value: `${one.key}.${field.fieldname}`, label: `${said(one)}: ${field.label}`, doctype: field.options })));

// the desk's own dialog, with its record pickers, asked while this one steps aside:
// two dialogs each keeping the focus to itself fight over it
function ask(fields, done, title, label) {
	open.value = false;
	const asked = prompt(fields, done, title, label);
	asked.onhide = () => {
		open.value = !placed;
		placed = false;
	};
}

function add() {
	const hasThis = sources.value.some((one) => one.kind === "this");
	const links = linksFrom();
	const offered = [...(hasThis ? [] : [{ value: "this", label: props.record ? __("This record ({0})", [__(props.record.doctype)]) : __("The record each copy is filed on") }]), { value: "record", label: kinds.record }, ...(links.length ? [{ value: "linked", label: __("A record linked from another") }] : []), { value: "list", label: kinds.list }];
	ask(
		[
			{ fieldname: "kind", fieldtype: "Select", label: __("Source"), options: offered, default: offered[0].value, reqd: 1 },
			{ fieldname: "doctype", fieldtype: "Link", options: "DocType", label: __("Record Type"), depends_on: props.record ? "eval:['record','list'].includes(doc.kind)" : "eval:doc.kind!='linked'", get_query: () => ({ filters: { istable: 0, issingle: 0 } }) },
			{ fieldname: "name", fieldtype: "Dynamic Link", options: "doctype", label: __("Record"), depends_on: props.record ? "eval:doc.kind=='record'" : "eval:['record','this'].includes(doc.kind)", description: props.record ? "" : __("For this, a record to show while you work.") },
			{ fieldname: "link", fieldtype: "Select", label: __("Linked From"), options: links, depends_on: "eval:doc.kind=='linked'" },
			{ fieldname: "where", fieldtype: "Data", label: __("Only Those Whose"), description: __("A field of the list's records, such as customer."), depends_on: "eval:doc.kind=='list'" },
			{ fieldname: "equals", fieldtype: "Data", label: __("Is"), description: __("A value, or a field of another source, such as {this.name}."), depends_on: "eval:doc.kind=='list'" },
			{ fieldname: "limit", fieldtype: "Int", label: __("At Most"), default: 10, depends_on: "eval:doc.kind=='list'" },
		],
		async (values) => {
			const one = { kind: values.kind };
			if (values.kind === "this") Object.assign(one, { doctype: props.record?.doctype || values.doctype, sample: values.name });
			if (values.kind === "record") Object.assign(one, { doctype: values.doctype, name: values.name });
			if (values.kind === "linked") {
				const link = links.find((it) => it.value === values.link);
				if (!link) return;
				const [from, field] = values.link.split(".");
				Object.assign(one, { from, field, doctype: link.doctype });
			}
			if (values.kind === "list") Object.assign(one, { doctype: values.doctype, limit: values.limit || 10, filters: values.where && values.equals ? [[values.where, "=", values.equals]] : [] });
			if (!one.doctype) return;
			one.key = values.kind === "this" ? "this" : keyFor(one.doctype);
			await saveSources([...sources.value, one]);
		},
		__("Add a Source"),
		__("Add"),
	);
}

async function remove(key) {
	delete fieldsOf[key];
	await saveSources(sources.value.filter((one) => one.key !== key));
}

function put(text) {
	addTextElement(text);
	open.value = false;
}

// a list as a table: a heading row, then a row of chips for each record it may hold
function asTable(one) {
	const offered = (fieldsOf[one.key] || []).map((field) => ({ label: field.label, value: field.fieldname }));
	// the columns its list shows, else the first few after its ID
	const shown = (fieldsOf[one.key] || []).filter((field) => field.in_list_view).map((field) => field.fieldname);
	const listed = (shown.length ? shown : offered.slice(1, 4).map((field) => field.value)).slice(0, 4);
	ask(
		[{ fieldname: "columns", fieldtype: "MultiCheck", label: __("Columns"), options: offered.map((field) => ({ ...field, checked: listed.includes(field.value) })), columns: 2, reqd: 1 }],
		({ columns }) => {
			if (!columns?.length) return;
			const heads = columns.map((name) => offered.find((field) => field.value === name)?.label || name);
			const rows = Array.from({ length: one.limit || 10 }, (_, at) => columns.map((name) => chip(one.key, `${at + 1}.${name}`)));
			const cell = (text, header = false) => ({ lines: [text], colspan: 1, rowspan: 1, header, style: header ? { bold: true } : {} });
			addTableElement([heads.map((text) => cell(text, true)), ...rows.map((row) => row.map((text) => cell(text)))]);
			placed = true;
		},
		__("Put In as a Table"),
		__("Put In"),
	);
}
</script>
