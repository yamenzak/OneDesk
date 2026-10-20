<!-- The records a link column can name (one_sheet/table.py, _rule), under the cell while it is typed in, drawn as the desk's own link field draws its list (frappe/public/js/frappe/form/controls/link.js and scss/common/awesomeplete.scss): the name in bold over its description, then Create a new … and Advanced Search. -->
<template>
	<div role="listbox" :style="box" @mousedown.prevent.stop>
		<div
			v-for="(one, n) in rows"
			:key="one.value"
			role="option"
			:aria-selected="n === at"
			:style="option(n)"
			@mouseenter="at = n"
			@click="choose(n)"
		>
			<p v-if="!one.action" :title="one.value" :style="text">
				<strong :style="{ fontWeight: 600 }">{{ one.label || one.value }}</strong>
				<template v-if="one.description && one.description !== one.value">
					<br /><span>{{ one.description }}</span>
				</template>
			</p>
			<p v-else :style="{ ...text, display: 'flex', alignItems: 'center' }">
				<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :style="{ marginRight: '5px', flex: 'none' }">
					<path v-if="one.icon === 'plus'" d="M12 5v14M5 12h14" />
					<template v-else><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></template>
				</svg>
				{{ one.label }}
			</p>
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { __, can, linkSelector, quickEntry } from "../../kit/desk";
import { call } from "../utils/api.js";

const props = defineProps({
	doctype: { type: String, required: true },
	query: { type: String, default: "" },
	x: { type: Number, default: 0 },
	y: { type: Number, default: 0 },
	w: { type: Number, default: 120 },
});
const emit = defineEmits(["pick", "close"]);
const found = ref([]);
const at = ref(0);
let asked = 0;
let timer = null;

const rows = computed(() => [
	...found.value,
	...(can("create", props.doctype) ? [{ value: "create_new__link_option", label: __("Create a new {0}", [__(props.doctype)]), icon: "plus", action: create }] : []),
	{ value: "advanced_search__link_option", label: __("Advanced Search"), icon: "search", action: advanced },
]);

const box = computed(() => ({
	position: "fixed",
	left: props.x + "px",
	top: props.y + "px",
	width: Math.max(props.w, 250) + "px",
	maxHeight: "min(60vh, 300px)",
	overflowY: "auto",
	overflowX: "hidden",
	zIndex: 8500,
	margin: 0,
	padding: "var(--padding-xs, 4px)",
	backgroundColor: "var(--bg-color, var(--surface-white))",
	border: "1px solid var(--border-color, var(--outline-gray-2))",
	borderRadius: "var(--radius, 8px)",
	boxShadow: "var(--shadow-md)",
}));
const text = { margin: 0, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitBoxOrient: "vertical", WebkitLineClamp: 4 };
function option(n) {
	return {
		cursor: "pointer",
		fontSize: "var(--text-sm, 13px)",
		lineHeight: 1.4,
		padding: "var(--padding-sm, 8px)",
		color: "var(--text-color, var(--ink-gray-9))",
		borderRadius: "var(--radius, 8px)",
		marginBottom: n < rows.value.length - 1 ? "var(--margin-xs, 4px)" : 0,
		backgroundColor: n === at.value ? "var(--awesomplete-hover-bg, var(--surface-gray-2))" : "transparent",
	};
}

function move(by) {
	const count = rows.value.length;
	if (count) at.value = (at.value + by + count) % count;
}

// Picks the highlighted row; false when there is none to pick.
function choose(n = at.value) {
	const one = rows.value[n];
	if (!one) return false;
	if (one.action) one.action();
	else emit("pick", one.value);
	return true;
}

function create() {
	emit("close");
	quickEntry(props.doctype, props.query, (doc) => emit("pick", doc.name));
}

function advanced() {
	emit("close");
	linkSelector(props.doctype, props.query, (value) => emit("pick", value));
}

async function search() {
	const mine = ++asked;
	try {
		const answer = await call("frappe.desk.search.search_link", { doctype: props.doctype, txt: props.query || "", page_length: 10 });
		if (mine !== asked) return;
		found.value = (Array.isArray(answer) ? answer : answer?.results || []).map((one) => (typeof one === "string" ? { value: one } : one));
		at.value = 0;
	} catch {
		if (mine === asked) found.value = [];
	}
}

watch(
	() => props.query,
	() => {
		clearTimeout(timer);
		timer = setTimeout(search, 120);
	},
	{ immediate: true },
);

defineExpose({ move, choose });
</script>
