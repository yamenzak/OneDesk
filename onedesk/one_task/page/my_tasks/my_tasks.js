// OneTask: the reader's tasks still to do, grouped by when they are due. Its
// body is the onedesk.my_tasks island (frontend/src/task/MyTasks.vue): its
// own column, as OneMail's and OneCalendar's are, so the rail is hidden.

frappe.pages["my-tasks"].on_page_load = (wrapper) => {
	onedesk.island_page(wrapper, { island: "onedesk.my_tasks", title: __("OneTask"), hide_sidebar: true, mark: "onetask" });
};
