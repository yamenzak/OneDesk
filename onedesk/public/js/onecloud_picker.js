// The upload dialog, joined to OneCloud. Frappe's dialog (every Attach field,
// the text editor's image, a comment, Data Import) keeps My Device, Link and
// Camera, and gains OneCloud: the explorer, to choose a file from anywhere
// the person may open — My Files, Company, what is shared with them, their
// libraries, any record's files — through the extension point Frappe gives
// for this, FileUploader.UploadOptions.
//
// Its own Library goes. It browsed Frappe's folder tree and asked Frappe's
// File permission, which knows nothing of a folder shared through OneCloud;
// two pickers answering "can I use that file" differently is worse than one.
//
// A file chosen is attached the way Library attached one — a new File row
// on the same object, so no bytes are copied — but through
// one_storage/api.py `attach`, which asks namespace.may, not Frappe's File
// permission. The explorer is loaded when OneCloud is first clicked.
frappe.provide("onedesk");

// What each open dialog was asked for — its on_success, its restrictions —
// which Frappe's component keeps to itself. Keyed by the mounted uploader,
// which is what an upload option is handed when clicked.
onedesk.uploader_options = new WeakMap();

onedesk.pick_from_onecloud = ({ dialog, uploader, doctype, docname, fieldname }) => {
	const props = onedesk.uploader_options.get(uploader) || {};
	const allowed = ((props.restrictions || {}).allowed_file_types || []).map((one) => one.toLowerCase());
	const several = props.allow_multiple !== false;
	const fits = (item) => {
		if (!allowed.length) return true;
		const name = (item.name || "").toLowerCase();
		const extension = name.split(".").pop();
		return allowed.some((one) =>
			one.endsWith("/*") ? onedesk.file_kinds.is(one.slice(0, -2), extension) : name.endsWith(one.startsWith(".") ? one : `.${one}`)
		);
	};
	let chosen = [];
	const picker = new frappe.ui.Dialog({
		title: __("Choose from OneCloud"),
		size: "extra-large",
		fields: [{ fieldtype: "HTML", fieldname: "explorer" }],
		primary_action_label: __("Attach"),
		primary_action: () => attach(chosen),
	});
	const attach = async (items) => {
		items = (items || []).filter(Boolean);
		if (!items.length) return frappe.show_alert({ message: __("Choose a file first."), indicator: "orange" });
		const refused = items.filter((one) => !fits(one));
		if (refused.length) {
			return frappe.msgprint(__("{0} is not a kind of file this takes.", [refused.map((one) => one.name).join(", ")]));
		}
		if (!several) items = items.slice(0, 1);
		const files = await frappe.xcall("onedesk.one_storage.api.attach", {
			nodes: items.map((one) => one.id),
			doctype: doctype || null,
			docname: docname || null,
			fieldname: fieldname || null,
		});
		// What Frappe's own upload does when a file arrives: the Attach field
		// takes its URL, the sidebar lists it, the editor inserts it.
		files.forEach((file) => props.on_success && props.on_success(file, { message: file }));
		picker.hide();
		dialog && dialog.hide();
	};
	picker.show();
	picker.get_primary_btn().prop("disabled", true);
	const $host = picker.fields_dict.explorer.$wrapper;
	frappe.require(["/assets/onedesk/css/onecloud.css", "/assets/onedesk/js/onecloud.js"]).then(() => {
		new onedesk.OneCloud(null, {
			parent: $host,
			picker: {
				start: "@my",
				on_select: (items) => {
					chosen = items;
					const $go = picker.get_primary_btn();
					$go.prop("disabled", !items.length);
					$go.text(items.length > 1 ? __("Attach {0} files", [items.length]) : __("Attach"));
				},
				on_pick: (items) => attach(items),
			},
		});
	});
};

// "image/*" and the like, against a file's extension, as the browser's
// own picker reads an accept list.
onedesk.file_kinds = {
	kinds: {
		image: ["png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "heic", "avif", "ico"],
		video: ["mp4", "mov", "webm", "mkv", "avi", "m4v"],
		audio: ["mp3", "wav", "ogg", "m4a", "flac", "aac"],
	},
	is(kind, extension) {
		return (this.kinds[kind] || []).includes(extension);
	},
};

frappe.require("file_uploader.bundle.js").then(() => {
	const Uploader = frappe.ui.FileUploader;
	if (!Uploader || Uploader.onecloud) return;
	class OneCloudUploader extends Uploader {
		constructor(options = {}) {
			super({ ...options, disable_file_browser: true });
			onedesk.uploader_options.set(this.uploader, options);
		}
	}
	OneCloudUploader.onecloud = true;
	frappe.ui.FileUploader = OneCloudUploader;
	Uploader.UploadOptions.push({
		label: __("OneCloud"),
		// Drawn like its neighbours: a disc, and Lucide's cloud from the sprite.
		icon: `<circle cx="15" cy="15" r="15" fill="var(--subtle-fg)"></circle>
			<use href="#icon-cloud" x="7" y="7" width="16" height="16" style="color: var(--text-color)"></use>`,
		action: (context) => onedesk.pick_from_onecloud(context),
	});
});
