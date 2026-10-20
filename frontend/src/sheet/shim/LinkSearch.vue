<!-- The records a link column can name (one_sheet/table.py, _rule): clicked open with its own search box, or under the cell while it is typed in. -->
<template>
	<div class="sn-dropdown-panel" :style="{ left: x + 'px', top: y + 'px', minWidth: Math.max(w, 240) + 'px', maxWidth: '420px', display: 'flex', flexDirection: 'column', gap: '2px', maxHeight: '300px' }" @mousedown.stop>
		<input
			v-if="!typing"
			ref="box"
			v-model="said"
			:style="{ width: '100%', padding: '6px 8px', marginBottom: '2px', border: '1px solid var(--outline-gray-2)', borderRadius: '6px', fontSize: '13px', background: 'var(--surface-white)', color: 'var(--ink-gray-9)', outline: 'none' }"
			:placeholder="__('Search {0}', [__(doctype)])"
			@keydown.down.prevent="move(1)"
			@keydown.up.prevent="move(-1)"
			@keydown.enter.prevent="found[at] && emit('pick', found[at].value)"
			@keydown.esc.prevent="emit('close')"
		/>
		<div
			v-for="(one, n) in found"
			:key="one.value"
			:style="{ display: 'flex', flexDirection: 'column', padding: '5px 10px', borderRadius: '6px', cursor: 'pointer', background: n === at ? 'var(--surface-gray-2)' : 'transparent' }"
			@mouseenter="at = n"
			@mousedown.prevent="emit('pick', one.value)"
		>
			<span :style="{ fontSize: '13px', color: 'var(--ink-gray-9)' }">{{ one.label || one.value }}</span>
			<span v-if="one.description" :style="{ fontSize: '12px', color: 'var(--ink-gray-5)' }">{{ one.description }}</span>
		</div>
		<div v-if="!found.length && !busy" :style="{ padding: '6px 10px', fontSize: '13px', color: 'var(--ink-gray-5)' }">{{ __("Nothing found") }}</div>
	</div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from "vue";
import { __ } from "../../kit/desk";
import { call } from "../utils/api.js";

const props = defineProps({
	doctype: { type: String, required: true },
	query: { type: String, default: "" },
	typing: { type: Boolean, default: false },
	x: { type: Number, default: 0 },
	y: { type: Number, default: 0 },
	w: { type: Number, default: 120 },
});
const emit = defineEmits(["pick", "close"]);
const box = ref(null);
const said = ref(props.query);
const found = ref([]);
const at = ref(0);
const busy = ref(false);
let asked = 0;
let timer = null;

// The description repeats the name first; only what it adds is shown.
function told(one) {
	const said = String(one.description || "");
	return said.startsWith(one.value) ? said.slice(String(one.value).length).replace(/^[\s,]+/, "") : said;
}

function move(by) {
	if (found.value.length) at.value = (at.value + by + found.value.length) % found.value.length;
}

async function search() {
	const mine = ++asked;
	busy.value = true;
	try {
		const answer = await call("frappe.desk.search.search_link", { doctype: props.doctype, txt: said.value || "", page_length: 10 });
		if (mine !== asked) return;
		found.value = (Array.isArray(answer) ? answer : answer?.results || []).map((one) => (typeof one === "string" ? { value: one } : { ...one, description: told(one) }));
		at.value = 0;
	} catch {
		if (mine === asked) found.value = [];
	} finally {
		if (mine === asked) busy.value = false;
	}
}

function soon() {
	clearTimeout(timer);
	timer = setTimeout(search, 150);
}

watch(said, soon);
watch(
	() => props.query,
	(now) => {
		said.value = now;
	},
);

onMounted(async () => {
	search();
	await nextTick();
	box.value?.focus();
});
</script>
