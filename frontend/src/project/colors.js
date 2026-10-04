// The colour each value is shown in, from frappe-ui's badge themes, the same
// on every view.
export const TASK_STATUS = { Open: "gray", Working: "blue", "Pending Review": "amber", Completed: "green", Cancelled: "red" };
export const PRIORITY = { Low: "gray", Medium: "blue", High: "amber", Urgent: "red" };
export const HEALTH = { "On Track": "green", "At Risk": "amber", "Off Track": "red" };
export const PROJECT_STATUS = { Open: "blue", Completed: "green", Cancelled: "gray" };

/** frappe-ui's surface for a theme, for a dot or a bar. */
export const SURFACE = { gray: "bg-surface-gray-5", blue: "bg-surface-blue-5", amber: "bg-surface-amber-5", green: "bg-surface-green-5", red: "bg-surface-red-5", violet: "bg-surface-violet-5" };

export const DONE = ["Completed", "Cancelled"];
