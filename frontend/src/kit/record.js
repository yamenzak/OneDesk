// A record on a page of its own, read and changed through desk
// (onedesk.record, public/js/record.js): the page puts `menu()`, frappe's own
// menu items, in its ··· menu. Its sidebar is frappe's own form sidebar, on
// the page's right, which desk draws (onedesk.island_page's `record`).
import { onBeforeUnmount, ref, shallowRef, unref, watch } from "vue";

import { formatted, onedesk } from "./desk";

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

// The record's own desk form, out of sight (onedesk.record.form): a page's
// fields are that form's controls, put where the field is shown (FieldEdit),
// so its client scripts, queries, depends_on and set_df_property all hold,
// and it saves as desk saves, against the `modified` it loaded. `version`
// moves on each refresh of the form and each change to one of its values.
export function useForm(doctype, name) {
	const frm = shallowRef(null);
	const version = ref(0);
	const listeners = new Set();
	let stop = null;

	watch(
		() => unref(name),
		async (now) => {
			stop?.();
			stop = null;
			frm.value = null;
			if (!now) return;
			const got = await desk().form(
				doctype,
				now,
				() => version.value++,
				(fieldname) => {
					version.value++;
					listeners.forEach((one) => one(fieldname));
				}
			);
			if (!got) return;
			if (unref(name) !== now) return got.stop();
			stop = got.stop;
			frm.value = got.frm;
		},
		{ immediate: true }
	);
	onBeforeUnmount(() => stop?.());

	return {
		frm,
		version,
		/** Runs `heard(fieldname)` on each change to a value; returns the way to stop. */
		edited(heard) {
			listeners.add(heard);
			return () => listeners.delete(heard);
		},
		/** The field's control on the form, as the form has it now. */
		control(fieldname) {
			version.value;
			return frm.value?.fields_dict?.[fieldname] || null;
		},
		/** "Write", "Read" or "None", as desk decides it for the form. */
		status(fieldname) {
			const control = this.control(fieldname);
			return control ? control.get_status() : null;
		},
		/** The value as the form shows it read-only. */
		shown(fieldname) {
			const control = this.control(fieldname);
			const doc = frm.value?.doc;
			if (!control || !doc) return "";
			const value = doc[fieldname];
			if (value === null || value === undefined || value === "") return "";
			return formatted(value, control.df, doc);
		},
		/** Lend the field's control to the page, floated over `spot` (onedesk.record.lend). */
		lend(fieldname, spot, hooks) {
			return frm.value ? desk().lend(frm.value, fieldname, spot, hooks) : null;
		},
		/** Set a value through the form, so its own scripts hear it. */
		set(fieldname, value) {
			return frm.value?.set_value(fieldname, value);
		},
		/** Reload the form once the record was changed somewhere else. */
		reload(modified) {
			const f = frm.value;
			if (f && !f.is_dirty() && modified && f.doc?.modified !== modified) f.reload_doc();
		},
	};
}
