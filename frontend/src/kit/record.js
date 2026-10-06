// A record's frame on a page of its own: what its form's menu and sidebar
// give it, read and changed through desk (onedesk.record, public/js/record.js).
// The page draws the sidebar with <Record> and puts `menu()` in its ··· menu.
import { onBeforeUnmount, ref, unref, watch } from "vue";

import { onedesk } from "./desk";

const desk = () => onedesk().record;

export function useRecord(doctype, name) {
	const record = ref(null);
	const said = ref(null);
	const can = ref({});
	const viewers = ref([]);
	let stop = [];

	async function reload() {
		const asked = unref(name);
		if (!asked) return;
		const got = await desk().read(doctype, asked);
		if (asked !== unref(name)) return;
		record.value = got;
		said.value = desk().said(got);
		can.value = desk().can(doctype, got);
	}

	watch(
		() => unref(name),
		(now) => {
			stop.forEach((one) => one());
			record.value = said.value = null;
			viewers.value = [];
			if (!now) return;
			stop = [desk().viewers(doctype, now, (users) => (viewers.value = users)), desk().changes(doctype, now, reload)];
			reload();
		},
		{ immediate: true }
	);
	onBeforeUnmount(() => stop.forEach((one) => one()));

	const after = (done) => async (...args) => {
		await done(...args);
		await reload();
	};
	return {
		doctype,
		record,
		said,
		can,
		viewers,
		reload,
		assign: () => desk().assign(doctype, unref(name), reload),
		unassign: after((user) => desk().unassign(doctype, unref(name), user)),
		share: () => desk().share(doctype, record.value, reload),
		tag: after((tag) => desk().tag(doctype, unref(name), tag)),
		untag: after((tag) => desk().untag(doctype, unref(name), tag)),
		tags: (txt) => desk().tags(doctype, txt),
		like: after((liked) => desk().like(doctype, unref(name), liked)),
		/** frappe's own menu items for the record; `gone` runs once it is deleted. */
		menu: (options = {}) => (record.value ? desk().menu(doctype, record.value, { changed: reload, ...options }) : []),
	};
}
