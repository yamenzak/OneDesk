<!-- A suggestion, where it was suggested.

     The card is the same `AI Proposal` the record's own screen shows; it is
     here because the moment somebody would answer it is the moment it was
     made, not the next time they remember to open a list. Answering it here
     and answering it there are the same two calls. -->
<template>
	<div class="one-ai-card">
		<div class="one-ai-card__what">{{ what }}</div>
		<div v-if="card.why" class="one-ai-card__why">{{ card.why }}</div>
		<pre v-if="changes" class="one-ai-card__changes">{{ changes }}</pre>

		<div v-if="card.state === 'Proposed'" class="one-ai-card__doing">
			<button class="btn btn-primary btn-xs" :disabled="busy" @click="answer('apply')">
				{{ __("Approve") }}
			</button>
			<button class="btn btn-default btn-xs" :disabled="busy" @click="answer('refuse')">
				{{ __("Refuse") }}
			</button>
		</div>
		<div v-else class="one-ai-card__state">{{ said }}</div>
	</div>
</template>

<script setup>
import { computed, ref } from "vue";

const __ = window.__;

const props = defineProps({ card: { type: Object, required: true } });
const emit = defineEmits(["answered"]);

const busy = ref(false);

const changes = computed(() => {
	const said = props.card.changes;
	if (!said) return "";
	try {
		return Object.entries(JSON.parse(said))
			.map(([field, value]) => `${field}: ${typeof value === "object" ? JSON.stringify(value) : value}`)
			.join("\n");
	} catch (e) {
		// A card whose changes will not parse is still a card worth showing.
		return said;
	}
});

// "Create a ToDo", "Edit ToDo TODO-0001" — the verb and the thing, because a
// card headed only "Create" makes somebody open the record to find out what.
const what = computed(() => {
	const named = [props.card.for_doctype, props.card.record].filter(Boolean).join(" ");
	const verb = { Create: __("Create"), Edit: __("Change"), Delete: __("Delete") }[props.card.kind];
	return `${verb || props.card.kind} ${named}`.trim();
});

const said = computed(() => {
	if (props.card.state === "Applied") return __("Approved — {0}", [props.card.applied_doc || __("done")]);
	if (props.card.state === "Refused") return __("Refused.");
	if (props.card.state === "Stale") return __("The record changed after this was suggested.");
	return props.card.state;
});

async function answer(verb) {
	busy.value = true;
	try {
		await frappe.xcall(`onedesk.one_ai.run.${verb}`, { proposal: props.card.name });
		emit("answered", props.card.name);
	} finally {
		busy.value = false;
	}
}
</script>
