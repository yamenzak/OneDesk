// A conversation's team state (one_mail/team.py): who has it, whether it is
// done, snoozed or due a reminder, and its notes; and what can be done to it.
// One per open conversation, read by its head and its panel alike.
import { computed, reactive, watch } from "vue";

import { __, asDateTime, call, can, dialog, prompt, toast } from "../kit";

const TEAM = "onedesk.one_mail.team.";
const MAKES = ["Lead", "Opportunity", "Issue", "Task", "Non Conformance", "Purchase Order"];

const at = (days, hour) => {
	const when = new Date();
	when.setDate(when.getDate() + days);
	when.setHours(hour, 0, 0, 0);
	return asDateTime(when);
};
const later = () => {
	const when = new Date(Date.now() + 3 * 3600 * 1000);
	when.setMinutes(0, 0, 0);
	return asDateTime(when);
};
const nextMonday = () => at(((8 - new Date().getDay()) % 7) || 7, 8);

function pick(title, done) {
	prompt({ fieldname: "at", fieldtype: "Datetime", label: __("When"), reqd: 1 }, ({ at: chosen }) => done(chosen), title, __("Save"));
}

function choose(title, options, done) {
	const asking = dialog({
		title,
		fields: [{ fieldname: "choice", fieldtype: "Select", label: title, options: options.map((one) => one.label).join("\n"), reqd: 1 }],
		primary_action_label: __("Save"),
		primary_action: ({ choice }) => {
			asking.hide();
			done(options.find((one) => one.label === choice));
		},
	});
	asking.show();
}

export function useTeam(where, { make = null, changed = () => {} } = {}) {
	const team = reactive({ said: { shared: false, assigned: [], notes: [], people: [], status: "Open" } });

	async function load() {
		const [account, thread] = where();
		if (!account || !thread) return;
		const got = await call(TEAM + "state", { account, thread });
		if (where()[1] === thread) team.said = got;
	}
	watch(where, load, { immediate: true });

	async function act(method, args, message) {
		const [account, thread] = where();
		team.said = await call(TEAM + method, { account, thread, ...args });
		if (message) toast(message);
		changed();
	}

	team.assignTo = computed(() => [
		...team.said.people.map((one) => ({ label: one.name, onClick: () => act("assign", { user: one.user }, __("Assigned to {0}.", [one.name])) })),
		...(team.said.assigned.length ? [{ label: __("Nobody"), icon: "lucide-user-x", onClick: () => act("assign", { user: null }, __("Unassigned.")) }] : []),
	]);
	team.snoozeOptions = computed(() => [
		{ label: __("Later Today"), onClick: () => act("snooze", { until: later() }, __("Snoozed.")) },
		{ label: __("Tomorrow Morning"), onClick: () => act("snooze", { until: at(1, 8) }, __("Snoozed.")) },
		{ label: __("Next Week"), onClick: () => act("snooze", { until: nextMonday() }, __("Snoozed.")) },
		{ label: __("Pick a Time"), onClick: () => pick(__("Snooze Until"), (until) => act("snooze", { until }, __("Snoozed."))) },
		...(team.said.snoozed_until ? [{ label: __("Back to Inbox Now"), onClick: () => act("snooze", { until: null }) }] : []),
	]);
	team.remindOptions = computed(() => [
		{ label: __("In 1 Day"), onClick: () => act("remind", { at: at(1, 9) }, __("Reminder set.")) },
		{ label: __("In 3 Days"), onClick: () => act("remind", { at: at(3, 9) }, __("Reminder set.")) },
		{ label: __("In a Week"), onClick: () => act("remind", { at: at(7, 9) }, __("Reminder set.")) },
		{ label: __("Pick a Time"), onClick: () => pick(__("Remind Me"), (when) => act("remind", { at: when }, __("Reminder set."))) },
		...(team.said.remind_at ? [{ label: __("No Reminder"), onClick: () => act("remind", { at: null }) }] : []),
	]);
	team.makeOptions = computed(() => (make ? MAKES.filter((one) => can("create", one)).map((one) => ({ label: __(one), onClick: () => make(one) })) : []));

	team.load = load;
	team.toggleDone = () =>
		act("done", { done: team.said.status === "Done" ? 0 : 1 }, team.said.status === "Done" ? __("Opened again.") : __("Marked done."));
	team.snoozeNow = () => choose(__("Snooze"), team.snoozeOptions, (one) => one?.onClick());
	team.assignNow = () => team.said.shared && choose(__("Assign"), team.assignTo, (one) => one?.onClick());
	team.take = (state) => (team.said = state);
	return team;
}
