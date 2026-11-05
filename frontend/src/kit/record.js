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
		menu: (options = {}) => (record.value ? desk().menu(doctype, record.value, { changed: reload, ...options }) : []),
	};
}

export function useForm(doctype, name, given = null) {
	const frm = shallowRef(null);
	const version = ref(0);
	const listeners = new Set();
	let stop = null;

	if (given) {
		frm.value = given;
		onBeforeUnmount(desk().heard(given, () => version.value++));
	} else watch(
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
				(fieldname, row) => {
					version.value++;
					listeners.forEach((one) => one(fieldname, row));
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
		edited(heard) {
			listeners.add(heard);
			return () => listeners.delete(heard);
		},
		control(fieldname) {
			version.value;
			return frm.value?.fields_dict?.[fieldname] || null;
		},
		status(fieldname) {
			const control = this.control(fieldname);
			return control ? control.get_status() : null;
		},
		value(fieldname) {
			version.value;
			return frm.value?.doc?.[fieldname];
		},
		df(fieldname) {
			return this.control(fieldname)?.df || null;
		},
		shown(fieldname) {
			const control = this.control(fieldname);
			const doc = frm.value?.doc;
			if (!control || !doc) return "";
			const value = doc[fieldname];
			if (value === null || value === undefined || value === "") return "";
			return formatted(value, control.df, doc);
		},
		lend(fieldname, spot, hooks) {
			return frm.value ? desk().lend(frm.value, fieldname, spot, hooks) : null;
		},
		row(table, row) {
			const doc = () => (version.value, frm.value ? desk().row(frm.value, table, row) : null);
			return {
				status: (fieldname) => (doc() ? desk().row_status(frm.value, table, row, fieldname) : null),
				shown(fieldname) {
					const one = doc();
					const value = one?.[fieldname];
					if (!one || value === null || value === undefined || value === "") return "";
					return formatted(value, desk().row_df(frm.value, table, row, fieldname), one);
				},
				value: (fieldname) => doc()?.[fieldname],
				df: (fieldname) => (doc() ? desk().row_df(frm.value, table, row, fieldname) : null),
				set: (fieldname, value) => (frm.value ? desk().set_row(frm.value, table, row, fieldname, value) : null),
				lend: (fieldname, spot, hooks) => (frm.value ? desk().lend_row(frm.value, table, row, fieldname, spot, hooks) : null),
			};
		},
		addRow(table, values) {
			if (!frm.value) return null;
			const name = desk().add_row(frm.value, table, values);
			version.value++;
			return name;
		},
		removeRow(table, row) {
			const f = frm.value;
			if (!f) return;
			f.set_value(table, (f.doc[table] || []).filter((one) => one.name !== row));
			f.dirty();
			version.value++;
		},
		async save() {
			const f = frm.value;
			if (f?.is_dirty()) await f.save();
			return !f?.is_dirty();
		},
		discard() {
			const f = frm.value;
			if (f?.is_dirty()) f.reload_doc();
		},
		set(fieldname, value) {
			return frm.value?.set_value(fieldname, value);
		},
		reload(modified) {
			const f = frm.value;
			if (f && !f.is_dirty() && modified && f.doc?.modified !== modified) f.reload_doc();
		},
	};
}
