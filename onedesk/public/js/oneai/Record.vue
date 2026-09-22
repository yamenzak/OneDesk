<!-- A record, drawn rather than described.

     What a person needs to recognise one is what type it is, what it is
     called, and a few fields — so a lookup shows that instead of a sentence
     saying a lookup happened. The same card carries a suggestion: the fields
     are the proposed values, and the two buttons are underneath. -->
<template>
	<div class="one-ai-rec" :class="{ 'one-ai-rec--suggested': suggested }">
		<div class="one-ai-rec__top">
			<span class="one-ai-rec__kind">{{ __(record.doctype) }}</span>
			<span class="one-ai-rec__id">{{ suggested ? verb : record.name }}</span>
			<span class="one-ai-rec__gap"></span>
			<button
				v-if="record.name"
				class="one-ai-icon one-ai-icon--sm"
				:title="__('Open')"
				@click="open"
			>
				<svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.5">
					<path d="M9 3h4v4M13 3 7.5 8.5M12 9.5V12a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1h2.5"
						stroke-linecap="round" stroke-linejoin="round" />
				</svg>
			</button>
			<button
				v-if="record.name"
				class="one-ai-icon one-ai-icon--sm"
				:title="__('Copy link')"
				@click="copy"
			>
				<svg viewBox="0 0 16 16" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.5">
					<rect x="5.5" y="5.5" width="7" height="7" rx="1.5" />
					<path d="M10.5 3.5h-6a1 1 0 0 0-1 1v6" stroke-linecap="round" />
				</svg>
			</button>
		</div>

		<div v-if="record.title" class="one-ai-rec__title">{{ record.title }}</div>

		<dl v-if="record.fields.length" class="one-ai-rec__fields" :class="{ 'one-ai-rec__fields--prose': prose }">
			<template v-for="field in record.fields" :key="field.label">
				<dt>{{ field.label }}</dt>
				<dd>{{ field.value }}</dd>
			</template>
		</dl>

		<div v-if="suggested && state === 'Proposed'" class="one-ai-rec__doing">
			<button class="btn btn-primary btn-xs" :disabled="busy" @click="answer('apply')">
				{{ __("Approve") }}
			</button>
			<button class="btn btn-default btn-xs" :disabled="busy" @click="answer('refuse')">
				{{ __("Refuse") }}
			</button>
		</div>
		<div v-else-if="suggested" class="one-ai-rec__state">{{ settled }}</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";

const __ = window.__;

const props = defineProps({
	record: { type: Object, required: true },
	// A suggestion is the same card with a verb where the id would be and two
	// buttons underneath, because what is being approved is a record.
	suggested: { type: Object, default: null },
});
const emit = defineEmits(["answered"]);

const busy = ref(false);

// One field holding a paragraph — what a field's own control comes back with —
// is read top to bottom rather than squeezed into the label-value grid.
const prose = computed(() => {
	const fields = props.record.fields || [];
	return fields.length === 1 && String(fields[0].value || "").length > 80;
});
const state = computed(() => props.suggested && props.suggested.state);

const verb = computed(() => {
	const kind = props.suggested && props.suggested.kind;
	return { Create: __("Suggested"), Edit: __("Suggested change"), Delete: __("Suggested deletion") }[kind] || kind;
});

const settled = computed(() => {
	const card = props.suggested || {};
	if (card.state === "Applied") return __("Approved — {0}", [card.applied_doc || __("done")]);
	if (card.state === "Refused") return __("Refused.");
	if (card.state === "Stale") return __("The record changed after this was suggested.");
	return card.state;
});

function open() {
	frappe.set_route("Form", props.record.doctype, props.record.name);
}

function copy() {
	frappe.utils.copy_to_clipboard(
		`${window.location.origin}/app/${frappe.router.slug(props.record.doctype)}/${props.record.name}`
	);
}

// The form this suggestion is about, if it is the one open. Approving a change
// there puts the text into the form beside whatever the person has typed and
// not saved, and they save it the way they save anything — a save from here
// would either lose their edits or be refused as stale.
function form() {
	const card = props.suggested;
	const frm = window.cur_frm;
	if (!card || card.kind !== "Edit" || !frm || frm.doctype !== card.for_doctype) return null;
	return (card.record ? frm.docname === card.record : frm.is_new()) ? frm : null;
}

async function answer(what) {
	busy.value = true;
	try {
		const frm = what === "apply" ? form() : null;
		if (frm) {
			const out = await frappe.xcall("onedesk.one_ai.run.took", { proposal: props.suggested.name });
			for (const [fieldname, value] of Object.entries(out.changes || {})) {
				await frm.set_value(fieldname, value);
			}
			onedesk.oneai.wrote(frm, out.changes || {}, props.suggested.name);
		} else {
			await frappe.xcall(`onedesk.one_ai.run.${what}`, { proposal: props.suggested.name });
		}
		emit("answered", props.suggested.name);
	} finally {
		busy.value = false;
	}
}
</script>
