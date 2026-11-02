// What the window's keys do (one_interface/shortcuts.py; docs/READY.md,
// mechanism 19): moving about, and what every list, record and calendar has.
(() => {
	const does = onedesk.shortcuts.does;
	const win = () => onedesk.interface.current();
	const act = (name, fallback) => () => {
		const here = win();
		if (here) return here.act(name);
		if (fallback) fallback();
	};

	does("one_interface.search", (e) => frappe.search.open_awesomebar_from_global_search_shortcut && frappe.search.open_awesomebar_from_global_search_shortcut(e));
	does("one_interface.back", act("back", () => window.history.back()));
	does("one_interface.forward", act("forward", () => window.history.forward()));
	does("one_interface.up", act("up"));
	does("one_interface.details", act("details"));
	does("one_interface.refresh", () => {
		const here = win();
		if (here && here.$reload) return here.$reload.trigger("click");
		if (here && here.handlers && here.handlers.refresh) return here.act("refresh");
		if (window.cur_frm && cur_frm.page && cur_frm.page.wrapper.is(":visible")) return cur_frm.reload_doc();
		if (window.cur_list && cur_list.refresh) return cur_list.refresh();
	});
	does("one_interface.sidebar", () => frappe.app.sidebar && frappe.app.sidebar.toggle_width());

	// A list (and a board, a tree): its New; its own search box.
	does("one_interface.new", () => frappe.app.trigger_primary_action());
	does("one_interface.find", () => {
		const here = win();
		if (here && here.$search) here.$search.trigger("focus");
	});

	// A record.
	const frm = () => (window.cur_frm && cur_frm.page && cur_frm.page.wrapper.is(":visible") ? cur_frm : null);
	does("one_interface.save", () => {
		document.activeElement && document.activeElement.blur();
		frappe.app.trigger_primary_action();
	});
	does("one_interface.new_record", () => frm() && frappe.new_doc(frm().doctype));
	does("one_interface.print", () => frm() && frappe.model.can_print(frm().doctype, frm()) && frm().print_doc());
	does("one_interface.previous", () => frm() && !frm().is_new() && frm().navigate_records(1));
	does("one_interface.next", () => frm() && !frm().is_new() && frm().navigate_records(0));

	// A calendar.
	const calendar = () => window.cur_list && cur_list.calendar && cur_list.calendar.fullCalendar ? cur_list.calendar : null;
	const show = (view) => () => {
		const cal = calendar();
		if (!cal) return;
		cal.fullCalendar.changeView(view);
		if (cal.view_button_group && cal.view_button_group.set_value) cal.view_button_group.set_value(view);
	};
	does("one_interface.today", () => calendar() && calendar().fullCalendar.today());
	does("one_interface.later", () => calendar() && calendar().fullCalendar.next());
	does("one_interface.earlier", () => calendar() && calendar().fullCalendar.prev());
	does("one_interface.month", show("dayGridMonth"));
	does("one_interface.week", show("timeGridWeek"));
	does("one_interface.day", show("timeGridDay"));
})();
