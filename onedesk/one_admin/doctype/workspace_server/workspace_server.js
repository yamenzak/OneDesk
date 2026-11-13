frappe.ui.form.on("Workspace Server", {
	refresh(frm) {
		if (!frm.doc.connected) return;
		const server = frm.doc.server;
		const status = frm.doc.status;

		if (status === "Released") {
			frm.add_custom_button(__("Connect Again"), async () => {
				const said = await frappe.xcall("onedesk.one_admin.operator.connect_again", { server });
				show_command(__("Connect {0}", [server]), said.command, __("Run once on the machine as root within an hour."));
				frm.reload_doc();
			});
			return;
		}

		if (status === "Releasing") {
			frm.add_custom_button(__("Release Command"), () => release(frm));
			frm.add_custom_button(__("Finish Release"), async () => {
				const go = await onedesk.interface.ask({
					question: __("Finish releasing {0}?", [server]),
					effect: __("Do this once the line has run on the machine. Its tunnel, addresses and keys are then removed."),
					verb: __("Finish Release"),
					danger: true,
				});
				if (!go) return;
				await frappe.xcall("onedesk.one_admin.operator.finish_release", { server });
				frappe.show_alert({ message: __("{0} released.", [server]), indicator: "green" });
				frm.reload_doc();
			});
			return;
		}

		frm.add_custom_button(__("Release Server"), async () => {
			const go = await onedesk.interface.ask({
				question: __("Release {0}?", [server]),
				effect: __("{0}'s sessions are deleted, then a line you run on the machine removes the one-box container, its image and the one-copies user.", [server]),
				verb: __("Release Server"),
				danger: true,
			});
			if (go) release(frm);
		});
	},
});

async function release(frm) {
	const said = await frappe.xcall("onedesk.one_admin.operator.release_server", { server: frm.doc.server });
	show_command(__("Release {0}", [said.server]), said.command, __("Run once on the machine as root within an hour. When it has run, the server reads Released here."));
	frm.reload_doc();
}

function show_command(title, command, description) {
	const shown = new frappe.ui.Dialog({
		title,
		fields: [{ fieldname: "command", fieldtype: "Code", label: __("Command"), read_only: 1, default: command, description }],
		primary_action_label: __("Copy Command"),
		primary_action() {
			frappe.utils.copy_to_clipboard(command);
			shown.hide();
		},
	});
	shown.show();
}
