/**
 * One's agents (README.md): one Durable Object per agent per workspace, named
 * `{workspace}.{app}`. A workspace wakes an agent with a signed event; the agent
 * works through the workspace's own tools, each call carrying a token of its
 * own, so everything it reads and writes stays in the workspace and is done
 * there as the agent's user. What an agent does is the workspace's to say: the
 * event names the tool it runs, and each tool's answer names the steps after it
 * (`next`), a tool of its own or a hand-off to another agent, so a new agent
 * needs nothing here.
 */

import { Agent, getAgentByName, routeAgentRequest } from "agents";
import { mint, secretFor, verify, type Claims } from "./token.ts";

export interface Env {
	AGENT: DurableObjectNamespace<ModuleAgent>;
	ONE_SECRET: string;
}

export type Step = { tool: string; args?: Record<string, unknown>; to?: string };

export type Event = {
	kind: string;
	host: string;
	tool?: string;
	args?: Record<string, unknown>;
	from?: string;
	asked_by?: string;
};

type Answer = { next?: Step[] } | null;

export const MOST_STEPS = 50;

const TOOL = "/api/method/onedesk.one_ai.agents.api.tool";
const NAME = /^([a-z0-9][a-z0-9-]{0,62})\.([a-z][a-z_]{1,40})$/;
const HOST = /^[a-z0-9.-]+$/;
const APP = /^[a-z][a-z_]{1,40}$/;

export function named(name: string): { workspace: string; app: string } | null {
	const found = NAME.exec(name || "");
	return found ? { workspace: found[1], app: found[2] } : null;
}

export class ModuleAgent extends Agent<Env> {
	async onStart(): Promise<void> {
		this.sql`CREATE TABLE IF NOT EXISTS seen (jti TEXT PRIMARY KEY, until INTEGER)`;
		this.sql`CREATE TABLE IF NOT EXISTS handed (at INTEGER, from_app TEXT, to_app TEXT, reading TEXT)`;
	}

	async onRequest(request: Request): Promise<Response> {
		const who = named(this.name);
		if (!who || request.method !== "POST") return new Response("Not found", { status: 404 });
		const body = await request.text();
		const now = Math.floor(Date.now() / 1000);
		const secret = await secretFor(this.env.ONE_SECRET, who.workspace);
		const claims = await verify(secret, request.headers.get("x-one-agent-token") || "", "agents", body, now);
		if (!claims || claims.ws !== who.workspace || claims.agent !== who.app || !this.fresh(claims, now)) {
			return new Response("Forbidden", { status: 403 });
		}
		const event = JSON.parse(body) as Event;
		if (!HOST.test(event.host || "")) return new Response("Bad host", { status: 400 });
		await this.schedule(0, "work", { ...event, asked_by: claims.for }, { retry: { maxAttempts: 3 } });
		return Response.json({ queued: true }, { status: 202 });
	}

	fresh(claims: Claims, now: number): boolean {
		this.sql`DELETE FROM seen WHERE until < ${now}`;
		if (this.sql`SELECT jti FROM seen WHERE jti = ${claims.jti}`.length) return false;
		this.sql`INSERT INTO seen (jti, until) VALUES (${claims.jti}, ${claims.exp})`;
		return true;
	}

	async receive(event: Event): Promise<void> {
		const reading = typeof event.args?.reading === "string" ? event.args.reading : "";
		this.sql`INSERT INTO handed (at, from_app, to_app, reading) VALUES (${Date.now()}, ${event.from || ""}, ${named(this.name)?.app || ""}, ${reading})`;
		await this.schedule(0, "work", event, { retry: { maxAttempts: 3 } });
	}

	async work(event: Event): Promise<void> {
		const who = named(this.name);
		if (!who || !event.tool) return;
		const steps: Step[] = [{ tool: event.tool, args: event.args || {} }];
		for (let taken = 0; steps.length && taken < MOST_STEPS; taken++) {
			const step = steps.shift() as Step;
			if (step.to !== undefined) {
				if (!APP.test(step.to)) continue;
				await this.handOn(who.workspace, step.to, { ...event, tool: step.tool, args: step.args || {} });
				continue;
			}
			const answer = await this.tool<Answer>(who.workspace, event, step.tool, step.args || {});
			steps.push(...(answer?.next || []));
		}
	}

	async tool<T>(workspace: string, event: Event, tool: string, args: Record<string, unknown>): Promise<T> {
		const app = named(this.name)?.app || "";
		const body = JSON.stringify({ tool, args });
		const secret = await secretFor(this.env.ONE_SECRET, workspace);
		const token = await mint(secret, { aud: "workspace", ws: workspace, agent: app, tool, for: event.asked_by }, body, Math.floor(Date.now() / 1000));
		const answer = await fetch(`https://${event.host}${TOOL}`, {
			method: "POST",
			headers: { "content-type": "application/json", "x-one-agent-token": token },
			body,
		});
		if (!answer.ok) throw new Error(`${tool} answered ${answer.status}`);
		return ((await answer.json()) as { message: T }).message;
	}

	async handOn(workspace: string, to: string, event: Event): Promise<void> {
		const other = await getAgentByName(this.env.AGENT, `${workspace}.${to}`);
		await other.receive({ ...event, kind: "handed", from: named(this.name)?.app });
	}
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		return (await routeAgentRequest(request, env)) || new Response("Not found", { status: 404 });
	},
} satisfies ExportedHandler<Env>;
