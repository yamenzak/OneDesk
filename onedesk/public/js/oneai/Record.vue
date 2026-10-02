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

		<div v-if="many" class="one-ai-rec__gist">
			<div class="one-ai-rec__named">{{ record.fields.map((f) => f.label).join(" · ") }}</div>
			<button class="one-ai-rec__more" @click="unfolded = !unfolded">
				{{ unfolded ? __("Hide the changes") : __("See the changes") }}
			</button>
		</div>

		<dl
			v-if="record.fields.length && (!many || unfolded)"
			class="one-ai-rec__fields"
			:class="{ 'one-ai-rec__fields--prose': prose }"
		>
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
		<button v-if="folded && !many" class="one-ai-rec__more" @click="unfolded = !unfolded">
			{{ unfolded ? __("Show fewer") : __("Show {0} more", [folded]) }}
		</button>

		<button v-if="record.page" class="one-ai-rec__more" @click="see_page">
			{{ __("See the Page") }}
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
	return unfolded.value || many.value ? all : all.slice(0, FOLD);
});

// A change to more than a few fields is said as what it touches, not drawn as
// a table: the page it changes is the better place to read it, and Approve
// puts it there with every changed field marked.
const MANY = 4;
const many = computed(
	() => props.suggested && props.suggested.kind === "Edit" && (props.record.fields || []).length > MANY
);
const folded = computed(() => Math.max((props.record.fields || []).length - FOLD, 0));

// One field holding a paragraph — what a field's own control comes back with —
// is read top to bottom rather than squeezed into the label-value grid.
const prose = computed(() => {
	const fields = props.record.fields || [];
	return fields.length === 1 && String(fields[0].value || "").length > 80;
});
const state = computed(() => props.suggested && props.suggested.state);

const kind = computed(() => (props.suggested ? props.suggested.kind || "Create" : ""));

// A Setup card's glyph is what it would set up (one/ai_setup.py).
const SETUP = { report: "file-chart-column", dashboard: "layout-dashboard", mail: "mail-check", level: "shield-check", profile: "id-card", group: "users-round", hold: "eye", extension: "puzzle", record_type: "table-2" };

// A record, a new one, a change, a deletion or how a form looks — Lucide's own.
const glyph = computed(
	() => ({ Create: "file-plus", Edit: "file-pen", Delete: "trash-2", Customize: "settings-2", Signature: "pen-line", Holidays: "calendar-days", Reply: "reply", Numbering: "hash", Printing: "printer", Approval: "route" })[kind.value] ||
		SETUP[props.record.what] ||
		"file"
);


const doctype = computed(() => props.record.doctype || (props.suggested && props.suggested.for_doctype) || "");

// What the card is, as a person would say it: the record's own title for a
// lookup, and for a suggestion what approving it would do.
const title = computed(() => {
	const name = props.record.title || props.record.name;
	if (kind.value === "Create") return __("New {0}", [__(doctype.value)]);
	if (kind.value === "Edit" && many.value) {
		return __("{0} changes to {1}", [props.record.fields.length, name || __(doctype.value)]);
	}
	if (kind.value === "Edit") return name ? __("Change {0}", [name]) : __("Change {0}", [__(doctype.value)]);
	if (kind.value === "Delete") return __("Delete {0}", [name || __(doctype.value)]);
	if (kind.value === "Customize") return __("Customize {0}", [__(doctype.value)]);
	if (kind.value === "Signature") return __("Signature for {0}", [name]);
	if (kind.value === "Holidays") return __("Holidays in {0}", [name]);
	if (kind.value === "Numbering") return __("Numbering of {0}", [__(doctype.value)]);
	if (kind.value === "Printing") return __("Printing of {0}", [__(doctype.value)]);
	if (kind.value === "Approval") return __("Approval of {0}", [__(doctype.value)]);
	if (kind.value === "Reply") return __("A reply to {0}", [name]);
	// A Setup card says itself, already translated (one/ai_setup.py).
	if (kind.value === "Setup") return props.record.title || __(doctype.value);
	return name || __(doctype.value);
});

// What a Setup card sets up, said instead of the doctype under it.
const SETUP_SAID = { report: "Saved Report", dashboard: "Dashboard", mail: "Report by Mail", level: "Level", profile: "Profile", group: "Group", hold: "What They See", extension: "Extension", record_type: "Record Type" };

const sub = computed(() => {
	const type = kind.value === "Setup" && SETUP_SAID[props.record.what] ? __(SETUP_SAID[props.record.what]) : __(doctype.value);
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

// A Printing card's page, drawn by the server as it would print, in a frame
// that runs nothing (printing.proposal_preview).
async function see_page() {
	const html = await frappe.xcall("onedesk.one.printing.proposal_preview", { proposal: props.suggested.name });
	const dialog = new frappe.ui.Dialog({ title: title.value, size: "extra-large" });
	const frame = document.createElement("iframe");
	frame.setAttribute("sandbox", "");
	frame.className = "one-ai-page";
	frame.srcdoc = html;
	dialog.$body.append(frame);
	dialog.show();
}

function open(name) {
	// A customization was applied to a form, not to a record of it.
	if (kind.value === "Customize") frappe.set_route("customize", doctype.value);
	// A mailbox's signature is set, and seen, in Settings › Mail.
	else if (kind.value === "Signature") frappe.set_route("settings", { section: "mail" });
	// The holidays are read, and changed by hand, on Workspace › Holidays.
	else if (kind.value === "Holidays") frappe.set_route("workspace-settings", { section: "holidays" });
	// A reply is read, and sent, in OneMail.
	else if (kind.value === "Reply") frappe.set_route("onemail");
	// A kind of record's series are read, and changed by hand, in its Settings.
	else if (kind.value === "Numbering") onedesk.doctype_settings.open(doctype.value, "naming");
	// A format it designed opens in frappe's builder, to be changed there like any other.
	else if (kind.value === "Printing" && props.record.format) frappe.set_route("print-format-builder", props.record.format);
	// Letter heads and defaults are read, and changed by hand, on Workspace › Printing.
	else if (kind.value === "Printing") frappe.set_route("workspace-settings", { section: "printing" });
	// An approval it made opens in frappe's workflow builder, to be changed there.
	else if (kind.value === "Approval") frappe.set_route("workflow-builder", name);
	// What it set up opens where it is kept: a report, a level's page, Show In's place.
	else if (kind.value === "Setup" && props.record.route) frappe.set_route(...props.record.route);
	else frappe.set_route("Form", doctype.value, name);
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

// A new message written for the email window that is still open.
function writes() {
	const card = props.suggested;
	const writing = onedesk.oneai.writing;
	return !!(
		card &&
		card.kind === "Edit" &&
		card.for_doctype === "Communication" &&
		!card.record &&
		writing &&
		writing.composer.dialog.display
	);
}

async function answer(what) {
	busy.value = true;
	try {
		const frm = what === "apply" ? form() : null;
		if (what === "apply" && kind.value === "Reply") {
			// Nothing is sent: the reply opens in frappe's email window, as Reply
			// opens it, to be read, changed and sent (onemail.js reply_to).
			const out = await frappe.xcall("onedesk.one_ai.run.apply", { proposal: props.suggested.name });
			const said = out.reply || {};
			await frappe.require(["/assets/onedesk/css/onemail.css", "/assets/onedesk/js/onemail.js"]);
			await onedesk.OneMail.reply_to(said.account, said.thread, { text: said.text });
		} else if (what === "apply" && writes()) {
			// Into the open email window, its signature and quoted message kept.
			const out = await frappe.xcall("onedesk.one_ai.run.took", { proposal: props.suggested.name });
			onedesk.oneai.rewrite((out.changes || {}).content || "");
		} else if (frm) {
			const out = await frappe.xcall("onedesk.one_ai.run.took", { proposal: props.suggested.name });
			for (const [fieldname, value] of Object.entries(out.changes || {})) {
				await frm.set_value(fieldname, value);
			}
			onedesk.oneai.wrote(frm, out.changes || {}, props.suggested.name);
			// Each field it changed is marked on the page with what it held, to be
			// read there and saved or undone the way anything on a form is.
			onedesk.oneai.changed(frm, props.record.fields || []);
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
