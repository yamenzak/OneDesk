(() => {
	const hrms = frappe.listview_settings["Employee Checkin"] || {};
	const hrms_onload = hrms.onload;

	// The list checks in the way the dock does: through One's clock, with its
	// gates, in the direction the clock says. hrms's own would read the last
	// log alone and say Check Out to somebody who never checked out yesterday.
	const paint = (listview) =>
		onedesk.clock.ready().then((ready) => {
			const direction = ready.direction || "";
			if (listview.one_painted === direction) return;
			listview.one_painted = direction;
			if (!direction) {
				listview.page.btn_primary.addClass("hide");
				return;
			}
			listview.page.set_primary_action(
				direction === "OUT" ? __("Check Out") : __("Check In"),
				() => onedesk.dock.punch().then(() => listview.refresh()),
				direction === "OUT" ? "circle-arrow-left" : "circle-arrow-right",
			);
		});

	frappe.listview_settings["Employee Checkin"] = Object.assign(hrms, {
		add_fields: ["attendance", "skip_auto_attendance", "one_outcome"],

		get_indicator: function (doc) {
			if (doc.skip_auto_attendance) {
				return [__("Rejected"), "red", "skip_auto_attendance,=,1"];
			}
			if (doc.attendance) {
				return [__("Counted"), "green", "attendance,is,set"];
			}
			if (doc.one_outcome === "Flagged") {
				return [__("Flagged"), "orange", "one_outcome,=,Flagged"];
			}
			return [__("Not counted yet"), "gray", "attendance,is,not set"];
		},

		onload: function (listview) {
			Object.defineProperty(listview, "set_primary_action", {
				get: () => () => paint(listview),
				set: () => {},
				configurable: true,
			});
			if (hrms_onload) hrms_onload(listview);
			if (!frappe.user.has_role(["HR User", "HR Manager"])) {
				listview.page.remove_inner_button(__("Add Checkin for Another Employee"));
			}
			paint(listview);
		},

		primary_action: function () {
			onedesk.dock.punch();
		},
	});
})();
