"""Every label and description this app adds reads like frappe's own.

`docs/WORDING.md` is the house style. This holds every doctype and every
custom field in the app to the parts of it a machine can check — the console
guard in test_console.py only ever covered One Admin, which is how the hiring
switches came to read like commit messages.

A description: at most 130 characters and two sentences, no first person, no
em dash, and a colon only after "Example". A label: Title Case, no full stop,
at most 60 characters, and a name rather than a sentence about somebody.
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

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
