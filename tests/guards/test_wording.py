"""Every label and description this app adds reads like frappe's own.

`docs/WORDING.md` is the house style. This holds every doctype and every
custom field in the app to the parts of it a machine can check — the console
guard in test_console.py only ever covered OneAdmin, which is how the hiring
switches came to read like commit messages.

A description: at most 130 characters and two sentences, no first person, no
em dash, and a colon only after "Example". A label: Title Case, no full stop,
at most 60 characters, and a name rather than a sentence about somebody.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

LONGEST = 130
VOICE = re.compile(r"\b(we|our|us|ours)\b", re.I)
SENTENCE = re.compile(r"^(The|What|Who|How|When|It|This|These)\s+\w")


def _fields():
	"""(where, label, description) for every field the app defines or adds."""
	for path in sorted(tree.APP.glob("*/custom/*.json")):
		for one in json.loads(path.read_text(encoding="utf-8")).get("custom_fields", []):
			yield f"{path.stem}.{one['fieldname']}", one.get("label") or "", one.get("description") or ""
	for path in sorted(tree.APP.glob("*/doctype/*/*.json")):
		spec = json.loads(path.read_text(encoding="utf-8"))
		if spec.get("doctype") != "DocType":
			continue
		for one in spec.get("fields", []):
			yield f"{path.stem}.{one['fieldname']}", one.get("label") or "", one.get("description") or ""


def _sentences(text: str) -> int:
	return len([one for one in re.split(r"(?<=[.!?])\s+", text.strip()) if one])


def test_every_description_is_one_or_two_plain_sentences():
	wrong = []
	for where, _label, said in _fields():
		if not said:
			continue
		if len(said) > LONGEST:
			wrong.append(f"{where}: {len(said)} characters")
		if _sentences(said) > 2:
			wrong.append(f"{where}: {_sentences(said)} sentences")
		if VOICE.search(said):
			wrong.append(f"{where}: first person")
		if "—" in said:
			wrong.append(f"{where}: em dash")
		if ":" in said.replace("Example:", ""):
			wrong.append(f"{where}: a colon, which is a note to self rather than help")
	assert not wrong, "out of register, see docs/WORDING.md:\n  " + "\n  ".join(wrong)


def test_every_label_is_a_name_not_a_sentence():
	wrong = []
	for where, label, _said in _fields():
		if not label:
			continue
		if label.endswith(".") or label[0].islower() or len(label) > 60:
			wrong.append(f"{where}: {label!r}")
		elif SENTENCE.match(label):
			wrong.append(f"{where}: {label!r} is a sentence")
	assert not wrong, "labels out of register, see docs/WORDING.md:\n  " + "\n  ".join(wrong)


SCREEN = re.compile(r'__\(\s*"((?:[^"\\]|\\.)*)"')
JOINED = re.compile(r"[a-z)\]][:;] \S| — |—")
LABELLED = re.compile(r"^\w+( \w+){0,2}: \{\d\}(, \{\d\})*$")
SCREEN_LONGEST = 140
NOTE = re.compile(r'note:\s*__\(\s*"((?:[^"\\]|\\.)*)"')
NOTE_LONGEST = 70
TELLING = re.compile(r"\b(Open one|Click (one|a|an|the|somebody|someone)|Tap one)\b")


def test_what_a_screen_says_is_plain():
	root = tree.APP / "public" / "js"
	found = []
	for path in sorted(root.rglob("*.js")):
		for one in SCREEN.finditer(path.read_text(encoding="utf-8")):
			text = one.group(1)
			if LABELLED.match(text):
				continue
			if JOINED.search(text) or len(text) > SCREEN_LONGEST or TELLING.search(text):
				found.append(f"  {path.relative_to(root)}: {text}")
		for one in NOTE.finditer(path.read_text(encoding="utf-8")):
			if len(one.group(1)) > NOTE_LONGEST:
				found.append(f"  {path.relative_to(root)}: note too long: {one.group(1)}")
	assert not found, "Write it plainly, as docs/WORDING.md says under On a Screen:\n" + "\n".join(found)


def test_no_screen_text_reads_like_a_commit_message():
	"""Field help is written the way frappe and erpnext write it.

	Theirs runs to a median of 68 characters, plain and instructional — "Zero
	means unlimited", "If enabled, changes to the document are tracked". Mine
	started as paragraphs lifted from the reasoning: four lines about ladder.py
	under a Select, on a screen somebody opens to find out whether a customer is
	paying. The reasoning belongs in docs/ and in the docstrings, which is what
	CLAUDE.md already says.

	Three things are checked, all of them proxies for the same thing. Length,
	because a paragraph is the usual symptom. First person, because "we" and
	"our" are the voice of an argument rather than of a field label. And the
	word `press`, because that is the name of Frappe Cloud's own app: correct
	in code, meaningless to the person reading the form.
	"""
	THEIR_APP = re.compile(r"\bpress\b", re.I)

	wrong = []
	for folder in sorted(one.name for one in (tree.APP / "one_admin" / "doctype").iterdir() if one.is_dir()):
		path = tree.APP / "one_admin" / "doctype" / folder / f"{folder}.json"
		if not path.exists():
			continue
		doc = json.loads(path.read_text(encoding="utf-8"))
		said = [("[doctype]", doc.get("description") or "")]
		said += [(one["fieldname"], one.get("description") or "") for one in doc["fields"]]
		for where, text in said:
			if not text:
				continue
			if len(text) > LONGEST:
				wrong.append(f"{folder}.{where}: {len(text)} characters")
			if VOICE.search(text):
				wrong.append(f"{folder}.{where}: first person")
			if THEIR_APP.search(text):
				wrong.append(f"{folder}.{where}: says press rather than Frappe Cloud")
	assert not wrong, "screen text out of register:\n  " + "\n  ".join(wrong)
