// A list of a kind of record with no title field heads its first column with
// frappe's "ID", over names like "Aluminium & Glazing" or "Installation".
// The column is the record's own name, so it says what kind it is.
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
