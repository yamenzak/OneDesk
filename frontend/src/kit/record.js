// A record on a page of its own, read and changed through desk
// (onedesk.record, public/js/record.js): the page puts `menu()`, frappe's own
// menu items, in its ··· menu. Its sidebar is frappe's own form sidebar, on
// the page's right, which desk draws (onedesk.island_page's `record`).
import { onBeforeUnmount, ref, unref, watch } from "vue";

import { onedesk } from "./desk";

const desk = () => onedesk().record;

export function useRecord(doctype, name) {
	const record = ref(null);
	const said = ref(null);
	const can = ref({});
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
			if (!now) return;
			stop = [desk().changes(doctype, now, reload)];
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
