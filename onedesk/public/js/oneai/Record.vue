<!-- A record, drawn rather than described.

     What a person needs to recognise one is what type it is, what it is
     called, and a few fields — so a lookup shows that instead of a sentence
     saying a lookup happened. The same card carries a suggestion: the fields
     are the proposed values, and the two buttons are underneath. -->
<template>
	<div class="one-ai-rec" :class="{ 'one-ai-rec--suggested': suggested }">
		<div class="one-ai-rec__head">
			<span class="one-ai-rec__glyph"><Icon :name="glyph" /></span>
			<div class="one-ai-rec__names">
				<div class="one-ai-rec__title">{{ title }}</div>
				<div class="one-ai-rec__sub">{{ sub }}</div>
			</div>
			<button v-if="record.name" class="one-ai-icon" :title="__('Open')" @click="open(record.name)">
				<Icon name="external-link" />
			</button>
		</div>

		<dl v-if="record.fields.length" class="one-ai-rec__fields" :class="{ 'one-ai-rec__fields--prose': prose }">
			<div v-for="field in fields" :key="field.label" class="one-ai-rec__field">
				<dt>{{ field.label }}</dt>
				<dd v-if="field.rows" class="one-ai-rec__rows">
					<div v-for="(row, i) in field.rows" :key="i" class="one-ai-rec__row">
						<div class="one-ai-rec__row-top">
							<span>{{ row.main }}</span>
							<span v-if="row.side" class="one-ai-rec__amount">{{ row.side }}</span>
						</div>
						<div v-if="row.notes.length" class="one-ai-rec__row-notes">
							{{ row.notes.join(" · ") }}
						</div>
					</div>
				</dd>
				<dd v-else-if="field.was !== undefined" class="one-ai-rec__change">
					<span class="one-ai-rec__was" :class="{ 'one-ai-rec__was--none': !field.was }">{{ field.was || __("empty") }}</span>
					<Icon name="arrow-right" size="xs" />
					<span>{{ field.value }}</span>
				</dd>
				<dd v-else>{{ field.value }}</dd>
			</div>
		</dl>
		<button v-if="folded" class="one-ai-rec__more" @click="unfolded = !unfolded">
			{{ unfolded ? __("Show fewer") : __("Show {0} more", [folded]) }}
		</button>

		<div v-if="suggested" class="one-ai-rec__foot" :class="`one-ai-rec__foot--${(state || '').toLowerCase()}`">
			<div v-if="suggested.why && state === 'Proposed'" class="one-ai-rec__why">{{ suggested.why }}</div>
			<div v-if="state === 'Proposed'" class="one-ai-rec__doing">
				<button class="one-ai-btn" :disabled="busy" @click="answer('refuse')">
					{{ __("Refuse") }}
				</button>
				<button class="one-ai-btn one-ai-btn--go" :disabled="busy" @click="answer('apply')">
					{{ __("Approve") }}
				</button>
			</div>
			<div v-else class="one-ai-rec__state">
				<Icon :name="state === 'Applied' ? 'check' : 'x'" />
				<span>{{ settled }}</span>
				<button
					v-if="state === 'Applied' && suggested.applied_doc"
					class="one-ai-rec__made"
					@click="open(suggested.applied_doc)"
				>
					{{ suggested.applied_doc }}
				</button>
			</div>
		</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";
import Icon from "./Icon.vue";

const __ = window.__;

const props = defineProps({
	record: { type: Object, required: true },
	// A suggestion is the same card with a verb where the id would be and two
	// buttons underneath, because what is being approved is a record.
	suggested: { type: Object, default: null },
});
const emit = defineEmits(["answered"]);

const busy = ref(false);

// Every field a card carries is on it — approving approves all of them — and
// past eight the rest wait behind a line that says how many.
const FOLD = 8;
const unfolded = ref(false);
const fields = computed(() => {
	const all = props.record.fields || [];
	return unfolded.value ? all : all.slice(0, FOLD);
});
const folded = computed(() => Math.max((props.record.fields || []).length - FOLD, 0));

// One field holding a paragraph — what a field's own control comes back with —
// is read top to bottom rather than squeezed into the label-value grid.
const prose = computed(() => {
	const fields = props.record.fields || [];
	return fields.length === 1 && String(fields[0].value || "").length > 80;
});
const state = computed(() => props.suggested && props.suggested.state);

const kind = computed(() => (props.suggested ? props.suggested.kind || "Create" : ""));

// A record, a new one, a change or a deletion — Lucide's own four.
const glyph = computed(
	() => ({ Create: "file-plus", Edit: "file-pen", Delete: "trash-2" })[kind.value] || "file"
);

const doctype = computed(() => props.record.doctype || (props.suggested && props.suggested.for_doctype) || "");

// What the card is, as a person would say it: the record's own title for a
// lookup, and for a suggestion what approving it would do.
const title = computed(() => {
	const name = props.record.title || props.record.name;
	if (kind.value === "Create") return __("New {0}", [__(doctype.value)]);
	if (kind.value === "Edit") return name ? __("Change {0}", [name]) : __("Change {0}", [__(doctype.value)]);
	if (kind.value === "Delete") return __("Delete {0}", [name || __(doctype.value)]);
	return name || __(doctype.value);
});

const sub = computed(() => {
	const type = __(doctype.value);
	if (props.suggested) return state.value === "Proposed" ? __("{0} · waiting for you", [type]) : type;
	const { name, title: called } = props.record;
	return called && name && called !== name ? `${type} · ${name}` : type;
});

const settled = computed(() => {
	const card = props.suggested || {};
	if (card.state === "Applied") return __("Approved");
	if (card.state === "Refused") return __("Refused.");
	if (card.state === "Stale") return __("The record changed after this was suggested.");
	return card.state;
});

function open(name) {
	frappe.set_route("Form", doctype.value, name);
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
	} catch {
		// The server already said why, in its own dialog; the card stays open.
	} finally {
		busy.value = false;
	}
}
</script>
