// How the Tasks, Board and Timeline views split tasks into groups, and which
// tasks they show: monday's "Group by" and search, over what `work` gave.
import { __, isPast } from "../kit";
import { DONE, SURFACE, TASK_STATUS } from "./colors";

export function visible(work, { search = "", showDone = false } = {}) {
	const words = search.trim().toLowerCase();
	return work.tasks.filter(
		(one) => (showDone || !DONE.includes(one.status)) && (!words || one.subject.toLowerCase().includes(words))
	);
}

export function groupTasks(work, tasks, by) {
	if (by === "status") {
		return work.statuses.map((status) => ({
			key: status,
			title: __(status),
			bar: SURFACE[TASK_STATUS[status] || "gray"],
			tasks: tasks.filter((one) => one.status === status),
			extra: { status },
		}));
	}
	if (by === "owner") {
		const owners = [...new Set(tasks.flatMap((one) => one.assigned))];
		return [
			...owners.map((user) => ({
				key: user,
				title: work.people[user]?.name || user,
				bar: SURFACE.blue,
				tasks: tasks.filter((one) => one.assigned[0] === user),
			})),
			{ key: "", title: __("Unassigned"), bar: SURFACE.gray, tasks: tasks.filter((one) => !one.assigned.length) },
		];
	}
	if (by === "due") {
		const week = new Date();
		week.setDate(week.getDate() + 7);
		const soon = week.toISOString().slice(0, 10);
		const late = (one) => one.exp_end_date && isPast(one.exp_end_date) && !DONE.includes(one.status);
		return [
			{ key: "late", title: __("Late"), bar: SURFACE.red, tasks: tasks.filter(late) },
			{ key: "week", title: __("Next 7 Days"), bar: SURFACE.amber, tasks: tasks.filter((one) => !late(one) && one.exp_end_date && one.exp_end_date <= soon) },
			{ key: "later", title: __("Later"), bar: SURFACE.blue, tasks: tasks.filter((one) => one.exp_end_date && one.exp_end_date > soon) },
			{ key: "none", title: __("No Due Date"), bar: SURFACE.gray, tasks: tasks.filter((one) => !one.exp_end_date) },
		];
	}
	return work.groups.map((group, i) => ({
		key: group.key,
		title: group.title,
		route: group.own ? null : `/desk/project/${group.key}`,
		bar: [SURFACE.blue, SURFACE.green, SURFACE.violet, SURFACE.amber, SURFACE.red][i % 5],
		tasks: tasks.filter((one) => one.project === group.key),
		project: group.key,
	}));
}

// A group's tasks with each sub-task under its parent (ERPNext's Parent
// Task), how deep it sits, and for a parent how many of its own are done.
export function nest(tasks) {
	const here = new Set(tasks.map((one) => one.name));
	const under = {};
	for (const one of tasks) {
		const parent = one.parent_task && here.has(one.parent_task) ? one.parent_task : "";
		(under[parent] ||= []).push(one);
	}
	const out = [];
	const walk = (parent, depth) => {
		for (const one of under[parent] || []) {
			const own = under[one.name] || [];
			out.push({ ...one, depth, sub: own.length, subDone: own.filter((child) => child.status === "Completed").length });
			if (depth < 5) walk(one.name, depth + 1);
		}
	};
	walk("", 0);
	return out;
}
