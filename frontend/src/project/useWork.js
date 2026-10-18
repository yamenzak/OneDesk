import { computed, onBeforeUnmount, ref } from "vue";

import { assign, call, followList, insert, setValue, unassign } from "../kit";
import { DONE } from "./colors";
import { onlyArg } from "./only";

export function useWork(project, only) {
	const work = ref(null);
	let timer = null;

	async function load() {
		const asked = project.value;
		if (!asked) return;
		const got = await call("onedesk.one_project.view.work", { project: asked, ...onlyArg(only) });
		if (asked === project.value) work.value = got;
	}
	const soon = () => {
		clearTimeout(timer);
		timer = setTimeout(load, 400);
	};
	const stop = followList("Task", soon);
	onBeforeUnmount(() => {
		stop();
		clearTimeout(timer);
	});

	const find = (name) => work.value?.tasks.find((one) => one.name === name);

	async function set(name, fieldname, value) {
		const task = find(name);
		const before = task?.[fieldname];
		if (task) task[fieldname] = value;
		try {
			await setValue("Task", name, fieldname, value);
		} catch (error) {
			if (task) task[fieldname] = before;
			throw error;
		}
		soon();
	}

	async function add(group, subject, extra = {}) {
		const made = await insert({ doctype: "Task", subject, project: group, ...extra });
		await load();
		return made;
	}

	async function give(name, users) {
		users = [].concat(users);
		const task = find(name);
		if (task) task.assigned = [...new Set([...task.assigned, ...users])];
		await assign("Task", name, users);
		soon();
	}

	async function take(name, user) {
		const task = find(name);
		if (task) task.assigned = task.assigned.filter((one) => one !== user);
		await unassign("Task", name, user);
		soon();
	}

	const count = computed(() => work.value?.tasks.filter((one) => !DONE.includes(one.status)).length || 0);

	return { work, load, set, add, give, take, find, count };
}
