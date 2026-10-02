// An extension, from the administrator's side. Everything on it is OneAI's or
// the review's, so there is nothing to type and no Save: Turn On and Turn Off
// are its Record Head's verbs (one_studio/heads.py), and changing it is asking
// OneAI. Nothing is attached to it, handed to anybody or shared: an extension
// is the administrators' own.
frappe.ui.form.on("Extension", {
	refresh(frm) {
		frm.disable_save();
		frm.sidebar?.sidebar
			.find(".form-assignments, .form-attachments, .form-tags, .form-shared")
			.addClass("hidden");
	},
});
