"""Headlines OneAI finds for a workspace's News Source (one/news): one
Gemini call grounded with Google Search, billed to the workspace for the
tokens and for each search Google ran, at Google's list price. The model
writes a line per headline; only a publisher Google's search actually
found is named, and a run that searched nothing keeps nothing."""

from datetime import date

from onedesk.one_admin import faults, gateway, ledger, meter, pricing
from onedesk.one_admin.faults import Refused
from onedesk.one_ai import models

# Grounding is the model's choice and cannot be forced: the quick model is
# asked twice, then the one that searched every time we measured.
MODELS = ("google/gemini-3.5-flash-lite", "google/gemini-3.5-flash-lite", "google/gemini-3.8-flash")
MODEL = MODELS[0]
# What Google charges for one search a grounded Gemini 3 call runs, in dollars.
SEARCH_USD = 14 / 1000
# The most a run is held for: three tries, with their searches.
HELD_USD = 12 * SEARCH_USD + 0.05
MOST = 20
LONGEST = 600
TIMEOUT = 90
SPLIT = "|||"

# Asked as a plain question in one turn: a system instruction, or rules
# around the question, and the model answers from memory without searching.
QUESTION = (
	"What are the latest news stories, from the last two days, for this brief: {brief}?{where} "
	"Give {most}, one per line, written as: headline ||| one sentence ||| publisher's web domain. "
	"Write them in the language with the code {language}. Nothing else."
)


def asked(brief: str, country: str, language: str, most: int) -> str:
	"""What the model is asked. Pure."""
	where = f" Prefer news about or from the country with the code {country}." if country else ""
	return QUESTION.format(brief=brief.rstrip(".?"), where=where, most=most, language=language or "en")


def lines(text: str, found: set[str], most: int) -> list[dict]:
	"""The model's lines as headlines; a publisher is kept only when the
	search found its site. Pure."""
	out = []
	for line in (text or "").splitlines():
		parts = [part.strip(" *-•\t") for part in line.split(SPLIT)]
		if len(parts) < 2 or not parts[0]:
			continue
		site = (
			(parts[2] if len(parts) > 2 else "")
			.lower()
			.removeprefix("https://")
			.removeprefix("http://")
			.removeprefix("www.")
			.split("/")[0]
		)
		known = (
			site
			if site
			and any(site == one or one.endswith(f".{site}") or site.endswith(f".{one}") for one in found)
			else ""
		)
		out.append(
			{"title": parts[0][:200], "summary": parts[1][:400], "publisher": known, "publisher_site": known}
		)
		if len(out) >= most:
			break
	return out


def domains(grounding: dict) -> set[str]:
	"""The sites Google's search found, by the titles it gives them. Pure."""
	out = set()
	for one in (grounding or {}).get("groundingChunks") or []:
		title = ((one.get("web") or {}).get("title") or "").lower().removeprefix("www.")
		if "." in title and " " not in title:
			out.add(title)
	return out


def brief(tenant: str, brief: str, country: str = "", language: str = "en", most: int = 8) -> dict:
	"""Headlines for a brief, billed to the workspace: the tokens at the
	model's price and each search at Google's."""
	brief = " ".join((brief or "").split())[:LONGEST]
	if not brief:
		raise Refused("Say what OneAI should look for")
	most = max(1, min(int(most or 8), MOST))
	money = gateway._money()
	holding = ledger.reserve(
		tenant,
		HELD_USD * money["markup"] * money["per_dollar"],
		why=MODEL,
		reference="news",
		action="news_brief",
	)
	settings = gateway._settings()
	spent_usd, searches, text, grounding, model = 0.0, 0, "", {}, MODEL
	try:
		for model in MODELS:
			said = _ask(settings, tenant, model, asked(brief, country, language, most))
			used, _why = meter.read(model, said)
			spent_usd += pricing.bill(
				models.rates(model, on=date.today().isoformat()), used, money["markup"], money["per_dollar"]
			).usd
			candidate = (said.get("candidates") or [{}])[0]
			grounding = candidate.get("groundingMetadata") or {}
			searches = len(grounding.get("webSearchQueries") or [])
			spent_usd += searches * SEARCH_USD
			if searches:
				text = "".join(
					part.get("text", "") for part in (candidate.get("content") or {}).get("parts") or []
				)
				break
	except Exception:
		if spent_usd:
			ledger.commit(holding, spent_usd * money["markup"] * money["per_dollar"], spent_usd, model=model)
		else:
			ledger.release(holding)
		raise
	credits = spent_usd * money["markup"] * money["per_dollar"]
	ledger.commit(holding, credits, spent_usd, model=model)
	# headlines Google's search did not find are the model's memory, not news
	found = lines(text, domains(grounding), most) if searches else []
	return {"items": found, "searches": searches, "credits": credits, "model": model}


def _ask(settings: dict, tenant: str, model: str, question: str) -> dict:
	where = f"{gateway._google(settings)}/v1beta/models/{model.removeprefix('google/')}:generateContent"
	body = {
		"contents": [{"role": "user", "parts": [{"text": question}]}],
		"tools": [{"google_search": {}}],
		**({"generationConfig": models.quiet(model)} if models.quiet(model) else {}),
	}
	answer = gateway._post(
		model, where, gateway._headers(settings, True, tenant, {"job": "news_brief"}), body, TIMEOUT
	)
	if answer.status_code != 200:
		raise faults.raised(model, answer.status_code, answer.text[: faults.KEPT])
	return answer.json()
