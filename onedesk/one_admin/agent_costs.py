"""What the agents cost us on Cloudflare a month, per workspace: a Durable
Object per agent per workspace on the Agents SDK, with its SQLite database,
reached through a Worker (docs/ARC-AI.md). Each price is Cloudflare's on the
Workers Paid plan, read on 13 November 2026 at its `source`; the account's
allowances are shared as the plan's $5 is (`costs.TENANTS_SHARING`). The
models an agent asks are charged in credits like any OneAI call (AGENTS.md,
Under the hood, What One costs us). Pure."""

from dataclasses import dataclass, field

from onedesk.one_admin import costs, pricing
from onedesk.one_ai import models

MILLION = 1_000_000

READ_ON = "2026-11-13"
OBJECTS = "https://developers.cloudflare.com/durable-objects/platform/pricing/"
WORKERS = "https://developers.cloudflare.com/workers/platform/pricing/"


@dataclass(frozen=True)
class Price:
	"""One Cloudflare meter: what the account gets free a month and what each
	unit past it costs in dollars."""

	included: float
	usd: float
	per: float = MILLION
	source: str = OBJECTS



PRICES = {
	"do_requests": Price(1 * MILLION, 0.15),
	"do_gb_s": Price(400_000, 12.50),
	"rows_read": Price(25_000 * MILLION, 0.001),
	"rows_written": Price(50 * MILLION, 1.00),
	"stored_gb": Price(5, 0.20, 1),
	"worker_requests": Price(10 * MILLION, 0.30, source=WORKERS),
	"worker_cpu_ms": Price(30 * MILLION, 0.02, source=WORKERS),
}

OBJECT_GB = 0.125


@dataclass(frozen=True)
class Use:
	"""How the agents are used, declared once. A message is one thing a
	person asks; each tool call goes back to the model, and the object stays
	in memory while it waits on the model, so that wait is billed."""

	agents: int = 20
	messages_a_person_a_day: float = 20
	workdays_a_month: float = 22
	tool_calls_a_message: float = 4
	wake_seconds_a_message: float = 30
	wakes_an_agent_a_day: float = 24
	wake_seconds_a_wake: float = 5
	rows_read_a_message: float = 200
	rows_written_a_call: float = 2
	stored_mb_an_agent: float = 50
	worker_cpu_ms_a_request: float = 10
	input_tokens_a_call: float = 2000
	cached_tokens_a_call: float = 4000
	output_tokens_a_call: float = 400


TYPICAL = Use()

LABELS = {
	"do_requests": "Durable Object requests",
	"do_gb_s": "Durable Object duration",
	"rows_read": "SQLite rows read",
	"rows_written": "SQLite rows written",
	"stored_gb": "SQLite storage",
	"worker_requests": "Worker requests",
	"worker_cpu_ms": "Worker CPU",
}


@dataclass
class Bill:
	"""A month of the agents for one workspace: what each meter counted, and
	what it costs in the price list's currency once the workspace's share of
	the allowance is taken off."""

	people: float
	counted: dict = field(default_factory=dict)
	lines: dict = field(default_factory=dict)

	@property
	def total(self) -> float:
		return round(sum(self.lines.values()), 4)

	def per_agent(self, use: Use = TYPICAL) -> float:
		return round(self.total / use.agents, 4) if use.agents else 0.0


def calls_a_message(use: Use = TYPICAL) -> float:
	"""Model calls a message makes: the first and one after each tool."""
	return 1 + use.tool_calls_a_message


def counted(people: float, use: Use = TYPICAL) -> dict:
	"""What a workspace of `people` makes each meter count in a month. Pure."""
	messages = people * use.messages_a_person_a_day * use.workdays_a_month
	wakes = use.agents * use.wakes_an_agent_a_day * 30
	requests = messages * calls_a_message(use) + wakes
	return {
		"do_requests": requests,
		"do_gb_s": (messages * use.wake_seconds_a_message + wakes * use.wake_seconds_a_wake) * OBJECT_GB,
		"rows_read": messages * use.rows_read_a_message,
		"rows_written": (messages * calls_a_message(use) + wakes) * use.rows_written_a_call,
		"stored_gb": use.agents * use.stored_mb_an_agent / 1024,
		"worker_requests": messages + wakes,
		"worker_cpu_ms": (messages + wakes) * use.worker_cpu_ms_a_request,
	}


def priced(meter: str, count: float, sharing: int) -> float:
	"""What a meter's count costs past the workspace's share of the
	allowance, in the price list's currency. Pure."""
	price = PRICES[meter]
	over = max(0.0, count - price.included / sharing)
	return costs.usd(over / price.per * price.usd)


def monthly(people: float, use: Use = TYPICAL, sharing: int = costs.TENANTS_SHARING) -> Bill:
	"""A month of the agents for a workspace of `people`, every one of them
	working. Pure."""
	made = counted(people, use)
	return Bill(people, made, {meter: round(priced(meter, count, sharing), 4) for meter, count in made.items()})


def total(people: float) -> float:
	"""A month of the agents for a workspace of `people` at typical use. Pure."""
	return monthly(people).total


def seat(use: Use = TYPICAL) -> float:
	"""What one more person costs a month with no allowance left: what an
	add-on's seats cost. Pure."""
	one, none = counted(1, use), counted(0, use)
	return round(sum(costs.usd((one[meter] - none[meter]) / PRICES[meter].per * PRICES[meter].usd) for meter in PRICES), 4)


def a_message(use: Use = TYPICAL) -> float:
	"""One message's Cloudflare cost with no allowance left. Pure."""
	return round(seat(use) / (use.messages_a_person_a_day * use.workdays_a_month), 8)


def model_cost(use: Use = TYPICAL, tier: str = models.USUAL) -> float:
	"""What the model calls of one message cost, at the model a conversation
	asks first at `tier` (one_ai/models.py). Pure."""
	calls = calls_a_message(use)
	usd, _missing = pricing.cost(
		models.rates(models.USE["talk"][tier][0]),
		[
			pricing.Use("input", "text", "tokens", use.input_tokens_a_call * calls),
			pricing.Use("cached", "text", "tokens", use.cached_tokens_a_call * calls),
			pricing.Use("output", "text", "tokens", use.output_tokens_a_call * calls),
		],
	)
	return costs.usd(usd)


def cheapest(use: Use = TYPICAL) -> str:
	"""The tier whose model makes a message cheapest, so that its Cloudflare
	cost weighs most on each credit: the worst case. Pure."""
	return min(models.TIERS, key=lambda tier: model_cost(use, tier))


def per_credit(credit_cost: float, use: Use = TYPICAL, tier: str | None = None) -> float:
	"""The Cloudflare cost each credit spent on an agent's message carries,
	when a credit costs us `credit_cost` of model: a message's Cloudflare
	cost over the credits its model calls are charged, at `tier` or else at
	the worst one. Pure."""
	credits = model_cost(use, tier or cheapest(use)) / credit_cost if credit_cost else 0
	return round(a_message(use) / credits, 8) if credits else 0.0
