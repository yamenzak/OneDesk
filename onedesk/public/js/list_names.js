(() => {
	const List = frappe.views.ListView;
	if (!List || List.prototype.one_named) return;
	List.prototype.one_named = true;
	const setup = List.prototype.setup_columns;
	List.prototype.setup_columns = async function (...args) {
		await setup.apply(this, args);
		const first = this.columns && this.columns[0];
		if (first && first.type === "Subject" && first.df && first.df.fieldname === "name" && !this.meta.title_field) {
			first.df = { ...first.df, label: this.doctype };
		}
	};
})();
