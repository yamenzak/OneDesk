// An automation's steps (one/automation/flow.py) as frappe's AutomationCanvas
// draws a flow: the trigger first, each step a column to the right, and a
// step that branches (If, Ask) with its arms stacked under one another, each
// arm a row of its own. A node's id is where its step sits: "0" is the first
// step, "0/then/1" the second of the first step's Then, "0/l2/0" the first
// of its third label's. Pure, so the builder's edits are tested alone.

export const COLUMN = 380;
export const ROW = 132;
export const START = "start";

export function armsOf(step, __) {
	if (step.type === "if") {
		return [
			{ key: "then", label: __("Then") },
			{ key: "else", label: __("Otherwise") },
		];
	}
	if (step.type !== "ask") return [];
	if (step.ask === "pick") {
		return [
			...(step.labels || []).map((one, n) => ({ key: `l${n}`, label: __("If it's {0}", [one.label || "…"]) })),
			{ key: "else", label: __("If it's none of these") },
		];
	}
	return [
		{ key: "then", label: __("If yes") },
		{ key: "else", label: __("If not") },
	];
}

export function armSteps(step, key) {
	if (key.startsWith("l")) return (step.labels || [])[Number(key.slice(1))]?.then || [];
	return step[key] || [];
}

function armList(step, key) {
	if (key.startsWith("l")) {
		const label = step.labels[Number(key.slice(1))];
		label.then = label.then || [];
		return label.then;
	}
	step[key] = step[key] || [];
	return step[key];
}

export function locate(steps, id) {
	const parts = id.split("/");
	let list = steps;
	for (let at = 0; at < parts.length - 1; at += 2) list = armList(list[Number(parts[at])], parts[at + 1]);
	return { list, index: Number(parts[parts.length - 1]) };
}

export function stepAt(steps, id) {
	if (!id || id === START) return null;
	const { list, index } = locate(steps, id);
	return list[index] || null;
}

export function add(steps, afterId, branch, step) {
	if (!afterId || afterId === START) {
		steps.unshift(step);
		return "0";
	}
	if (branch) {
		armList(stepAt(steps, afterId), branch).push(step);
		const placed = armSteps(stepAt(steps, afterId), branch);
		return `${afterId}/${branch}/${placed.length - 1}`;
	}
	const { list, index } = locate(steps, afterId);
	list.splice(index + 1, 0, step);
	return afterId.replace(/\d+$/, String(index + 1));
}

export function remove(steps, id) {
	const { list, index } = locate(steps, id);
	list.splice(index, 1);
}

export function move(steps, id, by) {
	const { list, index } = locate(steps, id);
	const to = index + by;
	if (to < 0 || to >= list.length) return id;
	list.splice(to, 0, list.splice(index, 1)[0]);
	return id.replace(/\d+$/, String(to));
}

export function lay(steps, start, describe, __) {
	const nodes = [{ id: START, position: { x: 0, y: 0 }, data: { ...start, start: true, terminal: !steps.length } }];
	const edges = [];
	const link = (from, to) => edges.push({ id: `${from.id}->${to}:${from.label || ""}`, source: from.id, target: to, label: from.label });

	const place = (list, prefix, col, row, from, continues) => {
		let sources = from;
		let height = 1;
		let x = col;
		list.forEach((step, n) => {
			const id = prefix ? `${prefix}/${n}` : String(n);
			const arms = armsOf(step, __);
			const last = n === list.length - 1;
			const node = { id, position: { x: x * COLUMN, y: row * ROW }, data: { ...describe(step), branching: arms.length > 0, terminal: !arms.length && last && !continues } };
			nodes.push(node);
			sources.forEach((one) => link(one, id));
			if (!arms.length) {
				sources = [{ id }];
				x += 1;
				return;
			}
			let below = row;
			let wide = 0;
			const ends = [];
			const empty = [];
			for (const arm of arms) {
				const inner = armSteps(step, arm.key);
				if (!inner.length) {
					empty.push(arm);
					ends.push({ id, label: arm.label });
					continue;
				}
				const placed = place(inner, `${id}/${arm.key}`, x + 1, below, [{ id, label: arm.label }], continues || !last);
				ends.push(...placed.ends);
				below += placed.height;
				wide = Math.max(wide, placed.width);
			}
			node.data.arms = empty;
			node.data.canContinue = last && !continues;
			height = Math.max(height, below - row, 1);
			sources = ends;
			x += 1 + wide;
		});
		return { ends: sources, height, width: x - col };
	};

	place(steps, "", 1, 0, [{ id: START }], false);
	return { nodes, edges };
}

export function shown(param, step) {
	return (param.shown || []).every(([key, values]) => values.includes(step[key] ?? ""));
}

export function made(value, catalogue, id) {
	if (value === "if") {
		const first = (catalogue.conditions || []).find((one) => one.kind === "text");
		return { type: "if", id, test: { any: false, items: first ? [{ field: first.key, op: "contains", value: "" }] : [] }, then: [], else: [] };
	}
	if (value === "ask") return { type: "ask", id, ask: "yes", question: "", then: [], else: [] };
	if (value === "stop") return { type: "stop" };
	const block = (catalogue.actions || []).find((one) => one.key === value);
	const step = { type: value };
	for (const param of block?.params || []) {
		if (param.default !== null && param.default !== undefined) step[param.key] = param.default;
		else if (param.type === "choice" && param.options.length) step[param.key] = param.options[0].value;
	}
	return step;
}

export function tree(group) {
	return {
		conjunction: group?.any ? "or" : "and",
		conditions: (group?.items || []).map((one) => ("items" in one ? tree(one) : one)),
	};
}

export function group(tree_) {
	return {
		any: tree_?.conjunction === "or",
		items: (tree_?.conditions || []).map((one) => ("conditions" in one ? group(one) : one)),
	};
}

export function bare(steps) {
	return JSON.parse(JSON.stringify(steps || []));
}
