"""What Workers AI and Google offer, written to onedesk/one_ai/models.json
(docs/AICENTER.md, Models). It replaces the catalogue the account synced
every night: run it by hand, read what it says, change one_ai/models.py.

    CLOUDFLARE_ACCOUNT_ID=… AI_GATEWAY_ID=… AI_GATEWAY_TOKEN=… \\
        python3 scripts/models.py [--resolve] [--alive]

The token needs AI Gateway Run and Workers AI Read. Google's models are
listed through the gateway, with the key it stores. Google's list leaves out
Veo, so the names Veo has used are asked for one by one. `--resolve` also
asks each `-latest` alias for one word, which costs a few tokens, to learn
the model it points to; `--alive` asks every Google model models.py uses that
writes text, because Google lists a model it has closed to new keys.
"""

import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "onedesk" / "one_ai" / "models.json"
sys.path.insert(0, str(ROOT))

from onedesk.one_ai import models  # noqa: E402

API = "https://api.cloudflare.com/client/v4/accounts/{account}"
GATEWAY = "https://gateway.ai.cloudflare.com/v1/{account}/{gateway}/google-ai-studio/v1beta"

# Workers AI's tasks, as the kinds in one_ai/models.py.
TASKS = {
	"Text Generation": "talk",
	"Text Embeddings": "embed",
	"Automatic Speech Recognition": "hear",
	"Text-to-Speech": "speak",
	"Text-to-Image": "picture",
	"Image-to-Text": "see",
	"Text Classification": "rank",
	"Translation": "translate",
	"Object Detection": "see",
	"Image Classification": "see",
	"Summarization": "talk",
}

# Google's names, as kinds, first match wins.
FAMILIES = (
	(r"^veo-", "video"),
	(r"^lyria-", "music"),
	(r"image|nano-banana|^imagen-", "picture"),
	(r"-tts", "speak"),
	(r"transcribe", "hear"),
	(r"embedding", "embed"),
	(r"-live|native-audio|live-translate", "live"),
	(r"^gemini-omni", "video"),
	(r"^(gemini|gemma)-", "talk"),
)

# Veo's names Google's list does not return, tried one by one.
VEO = [
	f"veo-{version}-{speed}generate-{stage}"
	for version in ("3.0", "3.1", "3.2", "3.5", "4.0", "4")
	for speed in ("", "fast-")
	for stage in ("preview", "001")
]


def _context() -> ssl.SSLContext:
	bundle = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
	return ssl.create_default_context(cafile=bundle) if bundle else ssl.create_default_context()


def _call(url: str, headers: dict, body: dict | None = None) -> tuple[int, dict]:
	data = json.dumps(body).encode() if body is not None else None
	# Cloudflare refuses Python's own user agent.
	request = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json", "User-Agent": "one-models/1"})
	try:
		with urllib.request.urlopen(request, context=_context(), timeout=90) as answer:
			return answer.status, json.loads(answer.read() or b"{}")
	except urllib.error.HTTPError as refused:
		try:
			return refused.code, json.loads(refused.read() or b"{}")
		except json.JSONDecodeError:
			return refused.code, {}


def _settings() -> dict:
	names = {"account": "CLOUDFLARE_ACCOUNT_ID", "gateway": "AI_GATEWAY_ID", "token": "AI_GATEWAY_TOKEN"}
	found = {key: os.environ.get(name) for key, name in names.items()}
	missing = [names[key] for key, value in found.items() if not value]
	if missing:
		raise SystemExit(f"Set {', '.join(missing)}.")
	return found


def workers(settings: dict) -> list[dict]:
	"""Every model Workers AI offers, as one_ai/models.py names it."""
	head = {"Authorization": f"Bearer {settings['token']}"}
	found, page = [], 1
	while True:
		status, said = _call(f"{API.format(**settings)}/ai/models/search?per_page=100&page={page}", head)
		if status != 200:
			raise SystemExit(f"Workers AI's list answered {status}: {said.get('errors')}")
		rows = said.get("result") or []
		found += rows
		if len(rows) < 100:
			break
		page += 1
	return [_workers_model(one) for one in found]


def _workers_model(one: dict) -> dict:
	said = {prop["property_id"]: prop["value"] for prop in one.get("properties") or []}
	task = (one.get("task") or {}).get("name") or ""
	kind = "decide" if one["name"].startswith("@cf/cloudflare/clef") else "extract" if one["name"] == "@cf/cloudflare/clairic" else TASKS.get(task, "other")
	return {
		"id": one["name"],
		"company": "Cloudflare",
		"kind": kind,
		"context": int(said["context_window"]) if str(said.get("context_window", "")).isdigit() else None,
		"tools": said.get("function_calling") == "true",
		"vision": said.get("vision") == "true",
		"thinks": said.get("reasoning") == "true",
		"preview": said.get("beta") == "true" or one["name"].startswith("@cf/cloudflare/"),
		"withdrawn_on": said.get("planned_deprecation_date"),
		"price": [{"unit": row["unit"], "usd": row["price"]} for row in said.get("price") or []],
	}


def google(settings: dict) -> list[dict]:
	"""Every model Google lists through our gateway, and the Veo models it
	answers for when asked by name."""
	base = GATEWAY.format(**settings)
	head = {"cf-aig-authorization": f"Bearer {settings['token']}", "cf-aig-collect-log-payload": "false"}
	found, page = [], ""
	while True:
		status, said = _call(f"{base}/models?pageSize=1000{'&pageToken=' + page if page else ''}", head)
		if status != 200:
			raise SystemExit(f"Google's list answered {status}: {said.get('error')}")
		found += said.get("models") or []
		page = said.get("nextPageToken")
		if not page:
			break
	listed = {one["name"] for one in found}
	for name in VEO:
		if f"models/{name}" in listed:
			continue
		status, said = _call(f"{base}/models/{name}", head)
		if status == 200:
			found.append(said)
	return [_google_model(one) for one in found]


def _google_model(one: dict) -> dict:
	name = one["name"].removeprefix("models/")
	kind = next((kind for pattern, kind in FAMILIES if re.search(pattern, name)), "other")
	ways = set(one.get("supportedGenerationMethods") or [])
	return {
		"id": f"google/{name}",
		"company": "Google",
		"kind": kind,
		"context": one.get("inputTokenLimit"),
		"tools": kind == "talk" and "generateContent" in ways,
		"vision": kind in ("talk", "picture", "video"),
		"thinks": bool(one.get("thinking")),
		"preview": "preview" in name or "exp" in name or "preview" in (one.get("version") or ""),
		"alias": name.endswith("-latest"),
		"withdrawn_on": None,
		"how": sorted(way for way in ways if not way.startswith("count")),
		"version": one.get("version"),
	}


def resolve(settings: dict, rows: list[dict]) -> None:
	"""Ask each alias for one word and keep the model that answered."""
	base = GATEWAY.format(**settings)
	head = {"cf-aig-authorization": f"Bearer {settings['token']}", "cf-aig-collect-log-payload": "false"}
	for one in rows:
		if one.get("alias") and one["kind"] == "talk":
			status, said = _call(
				f"{base}/models/{one['id'].removeprefix('google/')}:generateContent",
				head,
				{"contents": [{"role": "user", "parts": [{"text": "Say yes."}]}], "generationConfig": {"maxOutputTokens": 200}},
			)
			if status == 200 and said.get("modelVersion"):
				one["points_to"] = f"google/{said['modelVersion']}"


def alive(settings: dict, rows: list[dict]) -> None:
	"""Ask each Google model models.py uses for words, and mark the ones that
	refuse a new key; Gemini 2.5 Pro was listed and answered 404."""
	base = GATEWAY.format(**settings)
	head = {"cf-aig-authorization": f"Bearer {settings['token']}", "cf-aig-collect-log-payload": "false"}
	for one in rows:
		if one["company"] == "Google" and one["id"] in models.used() and one["kind"] == "talk":
			status, _said = _call(
				f"{base}/models/{one['id'].removeprefix('google/')}:generateContent",
				head,
				{"contents": [{"role": "user", "parts": [{"text": "Say yes."}]}], "generationConfig": {"maxOutputTokens": 300}},
			)
			one["answers"] = status == 200


def report(rows: list[dict]) -> list[str]:
	"""What one_ai/models.py should hear about."""
	known = {one["id"]: one for one in rows}
	said = []
	for model in sorted(models.used()):
		one = known.get(model)
		if not one:
			said.append(f"GONE      {model} is in one_ai/models.py but neither company lists it")
		elif one.get("answers") is False:
			said.append(f"GONE      {model} is listed but refuses to answer")
		elif one.get("withdrawn_on"):
			said.append(f"GOING     {model} is withdrawn on {one['withdrawn_on']}")
		elif one.get("preview") and model not in models.PREVIEWS:
			said.append(f"PREVIEW   {model} is a preview and PREVIEWS doesn't say why it is used")
	for one in rows:
		if one["company"] == "Google" and one["kind"] in ("talk", "picture", "music", "video", "hear", "embed"):
			if not one.get("alias") and one["id"] not in models.GOOGLE and one["id"] not in models.UNPRICED and one["id"] in models.used():
				said.append(f"UNPRICED  {one['id']} is used and has no price in GOOGLE")
		if one.get("points_to") and one["points_to"] not in models.used():
			said.append(f"NEWER     {one['id']} points to {one['points_to']}, which models.py doesn't use")
	was = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else {"models": []}
	before = {one["id"] for one in was["models"]}
	for one in rows:
		if one["id"] not in before and one["kind"] in ("talk", "decide", "extract", "picture", "music", "video", "hear"):
			said.append(f"NEW       {one['id']} ({one['company']}, {one['kind']})")
	for gone in sorted(before - set(known)):
		said.append(f"DROPPED   {gone} is no longer listed")
	return said


def main(argv: list[str]) -> None:
	settings = _settings()
	rows = workers(settings) + google(settings)
	if "--resolve" in argv:
		resolve(settings, rows)
	if "--alive" in argv:
		alive(settings, rows)
	said = report(rows)
	SNAPSHOT.write_text(
		json.dumps({"read_on": date.today().isoformat(), "models": sorted(rows, key=lambda one: one["id"])}, indent=1, ensure_ascii=False) + "\n",
		encoding="utf-8",
	)
	print(f"{len(rows)} models: {sum(one['company'] == 'Cloudflare' for one in rows)} on Workers AI, {sum(one['company'] == 'Google' for one in rows)} at Google")
	print("\n".join(said) or "Nothing to change in one_ai/models.py.")
	print(f"Wrote {SNAPSHOT.relative_to(ROOT)}")


if __name__ == "__main__":
	main(sys.argv[1:])
