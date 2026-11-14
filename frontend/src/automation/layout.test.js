import { describe, expect, it } from "vitest";

import { add, bare, group, lay, locate, made, move, remove, shown, stepAt, tree } from "./layout";

const __ = (text, args) => String(text).replace(/\{(\d+)\}/g, (_, i) => (args || [])[Number(i)] ?? "");
const said = (step) => ({ kicker: step.type, label: step.type });
const start = { kicker: "Trigger", label: "When a message arrives" };

const rule = () => [
	{ type: "if", id: "i", test: { items: [] }, then: [{ type: "star" }, { type: "read" }], else: [] },
	{ type: "ask", id: "a", ask: "pick", labels: [{ label: "Quote", then: [{ type: "stop" }] }, { label: "Bill", then: [] }], else: [{ type: "junk" }] },
	{ type: "move", folder: "F" },
];

describe("an automation drawn as a flow", () => {
	it("starts at the trigger, one column a step, branches stacked", () => {
		const { nodes, edges } = lay(rule(), start, said, __);
		expect(nodes.map((one) => one.id)).toEqual(["start", "0", "0/then/0", "0/then/1", "1", "1/l0/0", "1/else/0", "2"]);
		const at = Object.fromEntries(nodes.map((one) => [one.id, one]));
		expect(at["0"].data.branching && at["0"].data.arms.map((one) => one.key)).toEqual(["else"]);
		expect(at["1"].data.arms.map((one) => one.label)).toEqual(["If it's Bill"]);
		expect(at["1/else/0"].position.y).toBeGreaterThan(at["1/l0/0"].position.y);
		expect(at["2"].data.terminal && !at["0/then/1"].data.terminal).toBe(true);
		expect(edges.find((one) => one.source === "0" && one.target === "0/then/0").label).toBe("Then");
		expect(edges.filter((one) => one.target === "1").map((one) => one.source).sort()).toEqual(["0", "0/then/1"]);
	});

	it("is empty at its trigger alone, where a step is added first", () => {
		const { nodes } = lay([], start, said, __);
		expect(nodes).toHaveLength(1);
		expect(nodes[0].data.start && nodes[0].data.terminal).toBe(true);
	});
});

describe("the builder's edits", () => {
	it("add a step after another, into an arm, or first", () => {
		const steps = rule();
		expect(add(steps, "0/then/0", null, { type: "link" })).toBe("0/then/1");
		expect(stepAt(steps, "0/then/1").type).toBe("link");
		expect(add(steps, "0", "else", { type: "junk" })).toBe("0/else/0");
		expect(add(steps, "1", "l1", { type: "star" })).toBe("1/l1/0");
		expect(steps[1].labels[1].then).toEqual([{ type: "star" }]);
		expect(add(steps, "start", null, { type: "read" })).toBe("0");
		expect(steps[0]).toEqual({ type: "read" });
	});

	it("move a step within its own list and take it out", () => {
		const steps = rule();
		expect(move(steps, "0/then/0", 1)).toBe("0/then/1");
		expect(steps[0].then.map((one) => one.type)).toEqual(["read", "star"]);
		expect(move(steps, "0/then/1", 1)).toBe("0/then/1");
		remove(steps, "1/l0/0");
		expect(steps[1].labels[0].then).toEqual([]);
		expect(locate(steps, "2").index).toBe(2);
	});

	it("make a new step from what its block asks", () => {
		const catalogue = {
			conditions: [{ key: "attachment", kind: "flag" }, { key: "subject", kind: "text" }],
			actions: [{ key: "reply", params: [{ key: "with", type: "choice", default: "Text", options: [] }, { key: "once", type: "choice", default: null, options: [{ value: "conversation" }] }] }],
		};
		expect(made("if", catalogue, "x").test.items).toEqual([{ field: "subject", op: "contains", value: "" }]);
		expect(made("reply", catalogue, "x")).toEqual({ type: "reply", with: "Text", once: "conversation" });
		expect(made("stop", catalogue, "x")).toEqual({ type: "stop" });
	});

	it("keep a group of conditions as frappe's ConditionBuilder holds it, and back", () => {
		const test = { any: false, items: [{ field: "outside", value: true }, { any: true, items: [{ field: "subject", op: "contains", value: "x" }] }] };
		expect(tree(test)).toEqual({ conjunction: "and", conditions: [{ field: "outside", value: true }, { conjunction: "or", conditions: [{ field: "subject", op: "contains", value: "x" }] }] });
		expect(group(tree(test))).toEqual(test);
	});

	it("ask a param only when the one it follows has its value", () => {
		const param = { key: "text", shown: [["with", ["Text"]]] };
		expect(shown(param, { with: "Text" })).toBe(true);
		expect(shown(param, { with: "Agent" })).toBe(false);
		expect(shown({ key: "to" }, {})).toBe(true);
		expect(bare([{ a: 1 }])).toEqual([{ a: 1 }]);
	});
});
