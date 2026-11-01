frappe.provide("onedesk");

// OneCloud is an island (frontend/src/cloud); its frappe dialogs are desk's.
onedesk.cloud_assets = ["/assets/onedesk/js/onecloud_dialogs.js", "/assets/onedesk/css/onecloud_dialogs.css"];

// OneCloud inside something else: a record's files, or the picker. `props`
// are the island's (room, picker, onListed). Resolves to its handle.
// A dialog's field is put in the page a moment after the dialog shows, so the
// island waits for its box.
onedesk.mount_cloud = async ($host, props) => {
	await frappe.require(onedesk.cloud_assets);
	for (let tries = 0; !$host[0].isConnected && tries < 100; tries++) await new Promise((next) => setTimeout(next, 20));
	$host.addClass("one-cloud-host");
	const handle = frappe.ui.mount_island("onedesk.onecloud", $host[0], props);
	return handle.ready ? handle.ready.then(() => handle) : handle;
};

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
	picker.$wrapper.addClass("one-files-dialog");
	picker.show();
	picker.get_primary_btn().prop("disabled", true);
	// The folders are the window's tree (one_interface/nav_tree.js), in a box of the
	// dialog's own beside the island.
	const $box = picker.fields_dict.explorer.$wrapper
		.addClass("one-cloud-picker")
		.html(`<div class="one-cloud-picker-nav"></div><div class="one-cloud-picker-body"></div>`);
	onedesk.mount_cloud($box.children(".one-cloud-picker-body"), {
		picker: {
			nav: $box.children(".one-cloud-picker-nav")[0],
			start: "@my",
			onSelect: (items) => {
				chosen = items;
				const $go = picker.get_primary_btn();
				$go.prop("disabled", !items.length);
				$go.text(items.length > 1 ? __("Attach {0} files", [items.length]) : __("Attach"));
			},
			onPick: (items) => attach(items),
		},
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
