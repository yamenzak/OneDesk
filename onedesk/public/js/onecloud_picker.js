frappe.provide("onedesk");

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
			return frappe.msgprint(__("{0} isn't an allowed file type.", [refused.map((one) => one.name).join(", ")]));
		}
		if (!several) items = items.slice(0, 1);
		const files = await frappe.xcall("onedesk.one_storage.api.attach", {
			nodes: items.map((one) => one.id),
			doctype: doctype || null,
			docname: docname || null,
			fieldname: fieldname || null,
		});
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
		icon: `<circle cx="15" cy="15" r="15" fill="var(--subtle-fg)"></circle>
			<use href="#icon-onestorage" x="6" y="6" width="18" height="18"></use>`,
		action: (context) => onedesk.pick_from_onecloud(context),
	});
});
