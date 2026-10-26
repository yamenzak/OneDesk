"""Every label and description this app adds reads like frappe's own.

`docs/WORDING.md` is the house style. This holds every doctype and every
custom field in the app to the parts of it a machine can check — the console
guard in test_console.py only ever covered OneAdmin, which is how the hiring
switches came to read like commit messages.

A description: at most 130 characters and two sentences, no first person, no
em dash, and a colon only after "Example". A label: Title Case, no full stop,
at most 60 characters, and a name rather than a sentence.

A label is a sentence when it has an article, a pronoun or a verb in the
middle of it: "Old App Invoices" and "Net of Retention", not "The Old App
Has" or "What Was Billed After the Retention". "Is" and "Has" may start a
checkbox's label, as ERPNext's do ("Is Group", "Has Serial No"), and a
consent checkbox ("I agree to these") is a sentence on
purpose. A Select's options are held to it too, and so are the fields of
a dialog or a report's columns, in Python and in the desk's scripts.
"""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

LONGEST = 130
VOICE = re.compile(r"\b(we|our|us|ours)\b", re.I)
NEVER = set(
	"the a an it its this that these those which who what was were are does did have had been be".split()
)
LEADING = {"is", "has"}
LAYOUT = {"Section Break", "Tab Break", "Column Break", "HTML", "Button", "Heading"}
ROOTS = (tree.APP, tree.APP.parent / "private")
SKIPPED = {"node_modules", "dist", "locale", "one_demo"}


def sentence(label: str) -> bool:
	"""Whether a label reads as a sentence rather than a name. Pure."""
	if label.startswith("I "):
		return False
	words = [word.lower() for word in re.findall(r"[A-Za-z']+", label)]
	return bool(set(words) & NEVER or set(words[1:]) & LEADING or label.rstrip().endswith((".", "?", ":")))


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
		elif sentence(label):
			wrong.append(f"{where}: {label!r} is a sentence")
	assert not wrong, "labels out of register, see docs/WORDING.md:\n  " + "\n  ".join(wrong)


def _files(*suffixes):
	for root in ROOTS:
		for path in root.rglob("*"):
			if path.suffix in suffixes and path.is_file() and not SKIPPED & set(path.parts):
				yield path


def _text(node):
	if isinstance(node, ast.Call) and node.args:
		node = node.args[0]
	if isinstance(node, ast.Constant) and isinstance(node.value, str):
		return node.value
	return None


def _keyed(node):
	if not isinstance(node, ast.Dict) or None in node.keys:
		return {}
	return {
		key.value: value
		for key, value in zip(node.keys, node.values, strict=True)
		if isinstance(key, ast.Constant)
	}


def _python():
	for path in _files(".py"):
		for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
			field = _keyed(node)
			if "fieldtype" not in field:
				continue
			if (label := _text(field.get("label"))) is not None:
				yield path, label
			if isinstance(field.get("options"), ast.List):
				for option in field["options"].elts:
					if (label := _text(_keyed(option).get("label"))) is not None:
						yield path, label


def _options():
	"""(where, option) for every Select option a doctype or custom field has."""
	for path in sorted(tree.APP.glob("*/custom/*.json")):
		for one in json.loads(path.read_text(encoding="utf-8")).get("custom_fields", []):
			if one.get("fieldtype") == "Select":
				yield from ((path, option) for option in (one.get("options") or "").split("\n") if option)
	for path in sorted(tree.APP.parent.glob("**/doctype/*/*.json")):
		if SKIPPED & set(path.parts):
			continue
		spec = json.loads(path.read_text(encoding="utf-8"))
		if spec.get("doctype") != "DocType":
			continue
		for one in spec.get("fields", []):
			if one.get("fieldtype") == "Select":
				yield from ((path, option) for option in (one.get("options") or "").split("\n") if option)


FIELD = re.compile(
	r"fieldtype:\s*\"[A-Za-z ]+\"[^{}]*?label:\s*__\(\"([^\"]+)\"\)|label:\s*__\(\"([^\"]+)\"\)[^{}]*?fieldtype:"
)
OPTION = re.compile(r"\{\s*value:\s*[^,{}]+,\s*label:\s*__\(\"([^\"]+)\"\)\s*\}")


def _desk():
	for path in _files(".js", ".vue"):
		source = path.read_text(encoding="utf-8", errors="ignore")
		for found in FIELD.finditer(source):
			yield path, found.group(1) or found.group(2)
		for found in OPTION.finditer(source):
			yield path, found.group(1)


def test_a_label_is_a_name_not_a_sentence():
	assert sentence("The Old App Has") and sentence("Invoice With the Retention In It")
	assert not sentence("Net of Retention") and not sentence("Is Group") and not sentence("Has Serial No")
	assert not sentence("I agree to these")


def test_every_option_and_dialog_field_is_a_name():
	found = sorted(
		{
			(str(path.relative_to(tree.APP.parent)), label)
			for source in (_options(), _python(), _desk())
			for path, label in source
			if sentence(label)
		}
	)
	assert not found, "labels that read as sentences, see docs/WORDING.md:\n" + "\n".join(
		f"  {path}: {label}" for path, label in found
	)


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


#: Phrasings that read as a person talking rather than a product reporting
#: (docs/WORDING.md, A message). Each was on a screen once.
CHATTY = re.compile(
	r"\bany more\b|\bof (its|their) own\b|\b(doesn|don)[’']t read\b|\bworks? out to\b"
	r"|\bdidn[’']t take\b|\bbeside\b|\bcouldn[’']t be made\b|\bwasn[’']t kept\b"
	r"|\bwhere everyone\b|\bisn[’']t there\b|\bholds something\b|^No \{0\} called\b",
	re.I,
)

MESSAGE = re.compile(r"""\b_{1,2}\(\s*(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')""")


def test_a_message_says_what_happened():
	"""Every translated string, in Python, the desk's scripts and the islands,
	is held to the message rule: the plain wording a SaaS product uses, not
	a person's turn of phrase."""
	found = []
	paths = [*tree.APP.rglob("*.py"), *(tree.APP / "public" / "js").rglob("*.js"), *(tree.APP.parent / "frontend" / "src").rglob("*.vue"), *(tree.APP.parent / "frontend" / "src").rglob("*.js")]
	for path in sorted(paths):
		if any(part in SKIPPED for part in path.parts) or tree.vendored(path) or path.name.startswith("test_"):
			continue
		for one in MESSAGE.finditer(path.read_text(encoding="utf-8")):
			text = one.group(1) or one.group(2) or ""
			if CHATTY.search(text):
				found.append(f"  {path.relative_to(tree.APP.parent)}: {text}")
	assert not found, "Say what happened, as docs/WORDING.md says under A message:\n" + "\n".join(found)


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
