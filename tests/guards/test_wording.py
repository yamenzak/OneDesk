"""Every label and description this app adds reads like frappe's own.

`docs/WORDING.md` is the house style. This holds every doctype and every
custom field in the app to the parts of it a machine can check — the console
guard in test_console.py only ever covered OneAdmin, which is how the hiring
switches came to read like commit messages.

A description, a hint and a note are one sentence, wherever they are written:
a field's description in a doctype or custom field, and a description, hint
or note in a module's code. What was two sentences when the rule settled at
one (13 November 2026) is counted per file in wording_allowed.py, which only
falls. A field's description is also at most 130 characters, with no first
person, no em dash, and a colon only after "Example". A label: Title Case, no
full stop, at most 60 characters, and a name rather than a sentence.

In a module on its way to ready (onedesk/one/ready.py) a heading (a tab, a
panel, a dialog, a section, a group, a field's label) is five words or fewer,
and no string says a word on the banned list.

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

from onedesk.one import ready  # noqa: E402
from tests.guards import wording_allowed  # noqa: E402

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
	for path in tree.scoped(sorted(tree.APP.glob("*/custom/*.json"))):
		for one in json.loads(path.read_text(encoding="utf-8")).get("custom_fields", []):
			yield f"{path.stem}.{one['fieldname']}", one.get("label") or "", one.get("description") or ""
	for path in tree.scoped(sorted(tree.APP.glob("*/doctype/*/*.json"))):
		spec = json.loads(path.read_text(encoding="utf-8"))
		if spec.get("doctype") != "DocType":
			continue
		for one in spec.get("fields", []):
			yield f"{path.stem}.{one['fieldname']}", one.get("label") or "", one.get("description") or ""


def sentences(text: str) -> int:
	return len([one for one in re.split(r"(?<=[.!?])\s+", text.strip()) if one])


def unplain_description(where: str, said: str) -> list[str]:
	"""What is out of register in a field's description. Pure."""
	wrong = []
	if len(said) > LONGEST:
		wrong.append(f"{where}: {len(said)} characters")
	if VOICE.search(said):
		wrong.append(f"{where}: first person")
	if "—" in said:
		wrong.append(f"{where}: em dash")
	if ":" in said.replace("Example:", ""):
		wrong.append(f"{where}: a colon, which is a note to self rather than help")
	return wrong


def test_every_description_is_plain():
	wrong = [one for where, _label, said in _fields() if said for one in unplain_description(where, said)]
	assert not wrong, "out of register, see docs/WORDING.md:\n  " + "\n  ".join(wrong)


QUOTED = r"""(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')"""
DESCRIBED = re.compile(r"\b(?:description|hint|note)\s*:\s*__\(\s*" + QUOTED + r"|\bheading(?:_with)?\(\s*__\([^)]*\)\s*,\s*__\(\s*" + QUOTED)


def _quoted(match: re.Match) -> str:
	return next((one for one in match.groups() if one is not None), "")


def described_in(file: str, source: str) -> list[str]:
	"""Every description, hint or note a file says. Pure."""
	if file.endswith(".json"):
		spec = json.loads(source)
		fields = spec.get("custom_fields", []) if "/custom/" in file else spec.get("fields", [])
		if "/doctype/" in file and spec.get("doctype") != "DocType":
			return []
		return [one["description"] for one in fields if one.get("description")]
	return [_quoted(one) for one in DESCRIBED.finditer(source)]


def _described() -> dict[str, str]:
	found = {}
	for path in tree.scoped([*tree.APP.glob("*/custom/*.json"), *tree.APP.glob("*/doctype/*/*.json")]):
		found[str(path.relative_to(tree.APP.parent))] = path.read_text(encoding="utf-8")
	for path in sorted(set(_files(".js", ".vue")) | {one for _module, one, _text in _read()}):
		if path.suffix in (".js", ".vue", ".py") and not path.name.startswith("test_"):
			found.setdefault(str(path.relative_to(tree.APP.parent)), path.read_text(encoding="utf-8", errors="ignore"))
	return found


def over_one_sentence(files: dict[str, str]) -> dict[str, int]:
	counted = {file: sum(sentences(said) > 1 for said in described_in(file, text)) for file, text in files.items()}
	return {file: count for file, count in counted.items() if count}


def test_a_description_is_one_sentence():
	found = over_one_sentence(_described())
	allowed = {file: count for file, count in wording_allowed.ALLOWED.items() if tree.judged(tree.ROOT / file)}
	over = {file: (count, allowed.get(file, 0)) for file, count in found.items() if count > allowed.get(file, 0)}
	assert not over, "a description, hint or note of more than one sentence (docs/WORDING.md): " + ", ".join(
		f"{file} has {count} (allowed {was})" for file, (count, was) in sorted(over.items())
	)
	fell = {file: found.get(file, 0) for file, was in allowed.items() if found.get(file, 0) < was}
	assert not fell, "fewer than wording_allowed.py allows; lower it: " + ", ".join(
		f"{file}: {count}" for file, count in sorted(fell.items())
	)


def test_the_one_sentence_rule_catches_its_example():
	assert over_one_sentence(
		{
			"onedesk/one_x/custom/item.json": '{"custom_fields": [{"description": "One. Two."}, {"description": "One."}]}',
			"onedesk/one_x/doctype/thing/thing.json": '{"doctype": "DocType", "fields": [{"description": "A. B. C."}]}',
			"onedesk/public/js/one_x/a.js": 'd.set({ hint: __("Typed here. Then saved."), note: __("Only one.") });',
			"onedesk/one_x/settings.py": 'heading_with(__("Mail"), __("Who it is from. And to."))',
		}
	) == {
		"onedesk/one_x/custom/item.json": 1,
		"onedesk/one_x/doctype/thing/thing.json": 1,
		"onedesk/public/js/one_x/a.js": 1,
		"onedesk/one_x/settings.py": 1,
	}


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
			if path.suffix in suffixes and path.is_file() and not SKIPPED & set(path.parts) and tree.judged(path):
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


def python_labels(nodes) -> list[str]:
	"""The labels and option labels of every field a Python file's nodes build. Pure."""
	out = []
	for node in nodes:
		field = _keyed(node)
		if "fieldtype" not in field:
			continue
		if (label := _text(field.get("label"))) is not None:
			out.append(label)
		if isinstance(field.get("options"), ast.List):
			for option in field["options"].elts:
				if (label := _text(_keyed(option).get("label"))) is not None:
					out.append(label)
	return out


def _python():
	for path in _files(".py"):
		yield from ((path, label) for label in python_labels(tree.walked(path)))


def select_options(fields) -> list[str]:
	"""Every option of the Select fields among `fields`. Pure."""
	return [option for one in fields if one.get("fieldtype") == "Select" for option in (one.get("options") or "").split("\n") if option]


def _options():
	"""(where, option) for every Select option a doctype or custom field has."""
	for path in tree.scoped(sorted(tree.APP.glob("*/custom/*.json"))):
		yield from ((path, option) for option in select_options(json.loads(path.read_text(encoding="utf-8")).get("custom_fields", [])))
	for path in tree.scoped(sorted(tree.APP.parent.glob("**/doctype/*/*.json"))):
		if SKIPPED & set(path.parts):
			continue
		spec = json.loads(path.read_text(encoding="utf-8"))
		if spec.get("doctype") != "DocType":
			continue
		yield from ((path, option) for option in select_options(spec.get("fields", [])))


FIELD = re.compile(
	r"fieldtype:\s*\"[A-Za-z ]+\"[^{}]*?label:\s*__\(\"([^\"]+)\"\)|label:\s*__\(\"([^\"]+)\"\)[^{}]*?fieldtype:"
)
OPTION = re.compile(r"\{\s*value:\s*[^,{}]+,\s*label:\s*__\(\"([^\"]+)\"\)\s*\}")


def desk_labels(source: str) -> list[str]:
	"""The labels of the fields and options a desk script builds. Pure."""
	return [found.group(1) or found.group(2) for found in FIELD.finditer(source)] + [found.group(1) for found in OPTION.finditer(source)]


def _desk():
	for path in _files(".js", ".vue"):
		yield from ((path, label) for label in desk_labels(path.read_text(encoding="utf-8", errors="ignore")))


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


DANGLING = re.compile(r"^(Its|It|Their|They|Them)\b|\bIts [A-Z]")


def unplain_on_screen(source: str) -> list[str]:
	"""What a desk script says that is not plain, or a note too long. Pure."""
	found = []
	for one in SCREEN.finditer(source):
		text = one.group(1)
		if LABELLED.match(text):
			continue
		if JOINED.search(text) or len(text) > SCREEN_LONGEST or TELLING.search(text) or DANGLING.search(text):
			found.append(text)
	found += [f"note too long: {one.group(1)}" for one in NOTE.finditer(source) if len(one.group(1)) > NOTE_LONGEST]
	return found


def test_what_a_screen_says_is_plain():
	"""The desk's own scripts and each doctype's: a button called "Its Items"
	sat in a doctype script, where this used not to look."""
	root = tree.APP
	paths = [*(root / "public" / "js").rglob("*.js"), *root.glob("*/doctype/*/*.js")]
	found = [f"  {path.relative_to(root)}: {text}" for path in tree.scoped(sorted(paths)) for text in unplain_on_screen(path.read_text(encoding="utf-8"))]
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


def chatty(source: str) -> list[str]:
	"""The translated strings of a source that read as a person talking. Pure."""
	return [text for one in MESSAGE.finditer(source) if CHATTY.search(text := one.group(1) or one.group(2) or "")]


def test_a_message_says_what_happened():
	"""Every translated string, in Python, the desk's scripts and the islands,
	is held to the message rule: the plain wording a SaaS product uses, not
	a person's turn of phrase."""
	found = []
	paths = [*tree.APP.rglob("*.py"), *(tree.APP / "public" / "js").rglob("*.js"), *(tree.APP.parent / "frontend" / "src").rglob("*.vue"), *(tree.APP.parent / "frontend" / "src").rglob("*.js")]
	for path in tree.scoped(sorted(paths)):
		if any(part in SKIPPED for part in path.parts) or tree.vendored(path) or path.name.startswith("test_"):
			continue
		found += [f"  {path.relative_to(tree.APP.parent)}: {text}" for text in chatty(path.read_text(encoding="utf-8"))]
	assert not found, "Say what happened, as docs/WORDING.md says under A message:\n" + "\n".join(found)


THEIR_APP = re.compile(r"\bpress\b", re.I)


def commit_like(where: str, text: str) -> list[str]:
	"""What makes a piece of OneAdmin's field help read like a commit message. Pure."""
	wrong = []
	if len(text) > LONGEST:
		wrong.append(f"{where}: {len(text)} characters")
	if VOICE.search(text):
		wrong.append(f"{where}: first person")
	if THEIR_APP.search(text):
		wrong.append(f"{where}: says press rather than Frappe Cloud")
	return wrong


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
	wrong = []
	for folder in sorted(one.name for one in (tree.APP / "one_admin" / "doctype").iterdir() if one.is_dir()):
		path = tree.APP / "one_admin" / "doctype" / folder / f"{folder}.json"
		if not path.exists() or not tree.judged(path):
			continue
		doc = json.loads(path.read_text(encoding="utf-8"))
		said = [("[doctype]", doc.get("description") or "")]
		said += [(one["fieldname"], one.get("description") or "") for one in doc["fields"]]
		wrong += [one for where, text in said if text for one in commit_like(f"{folder}.{where}", text)]
	assert not wrong, "screen text out of register:\n  " + "\n  ".join(wrong)


# Help written as reasoning rather than as frappe writes it: "Empty is the
# kind's usual", "such as Dubai", "which frees what an old TV holds on to".
# Frappe says "Leave empty to …", "Defaults to …" and "Example: …".
REASONING = re.compile(
	r"^Empty\b|\bEmpty (is|lets|tells|for|never|when|means)\b|\b[Ss]uch as\b|, so (a|an|the|it|they|its)\b"
	r"|\bwhich (frees|means)\b|\b(whoever|nobody|somebody)\b|\bholds on to\b"
	# a pronoun with nothing before it to point at, and two sentences glued with a semicolon:
	# "Its logo comes from here", "Older ones are deleted; 0 keeps them all"
	r"|^(Its|It|Their|They|Them)\b|;"
)
# Every module's field help, since News showed that a module left out of the
# list writes the register this rule exists to stop (docs/WORDING.md, The description).
REGISTERED = tuple(sorted(one.parent.name for one in tree.APP.glob("*/doctype")))


def reasoned(spec: dict) -> list[tuple[str, str]]:
	"""(where, text) for a doctype's help written as reasoning. Pure."""
	if spec.get("doctype") != "DocType":
		return []
	said = [("[doctype]", spec.get("description") or "")]
	said += [(one["fieldname"], one.get("description") or "") for one in spec.get("fields", [])]
	return [(where, text) for where, text in said if text and REASONING.search(text)]


def test_field_help_says_what_the_system_does():
	wrong = []
	for module in REGISTERED:
		for path in tree.scoped(sorted((tree.APP / module).glob("doctype/*/*.json"))):
			wrong += [f"{path.stem}.{where}: {text}" for where, text in reasoned(json.loads(path.read_text(encoding="utf-8")))]
	assert not wrong, "field help reads as reasoning, see docs/WORDING.md, The description:\n  " + "\n  ".join(wrong)


HEADING = re.compile(
	r"(?:\btitle|\bgroup|\blabel)\s*:\s*__\(\s*" + QUOTED
	+ r"""|:label="__\(\s*""" + QUOTED
	+ r"|\bheading(?:_with)?\(\s*__\(\s*" + QUOTED
)
SAID = re.compile(r"\b_{1,2}\(\s*" + QUOTED)
HEADING_WORDS = 5
BANNED = re.compile(
	r"\b(simply|just|easily|please|utili[sz]e|leverage|seamless(?:ly)?|powerful|robust|note that"
	r"|in order to|functionality|are you sure|something went wrong|frappe|erpnext)\b",
	re.I,
)


def _read():
	"""Every script of every module in onedesk/one/ready.py, ready or on its
	way, so a module being made ready is held to them from the start."""
	for module in ready.MODULES:
		for path in tree.scoped(ready.files(module)):
			if path.suffix in (".js", ".vue", ".py") and not path.name.startswith("test_"):
				yield module, path, path.read_text(encoding="utf-8")


def long_headings(text: str) -> list[str]:
	"""The headings a script says in more than five words. Pure."""
	return [_quoted(one) for one in HEADING.finditer(text) if len(_quoted(one).split()) > HEADING_WORDS]


def banned_said(text: str) -> list[str]:
	"""The strings a script shows that say a banned word. Pure."""
	return [_quoted(one) for one in SAID.finditer(text) if BANNED.search(_quoted(one))]


def test_a_heading_is_five_words_or_fewer():
	found = [f"  {module} {path.name}: {said}" for module, path, text in _read() for said in long_headings(text)]
	assert not found, "A heading is five words or fewer (docs/WORDING.md):\n" + "\n".join(found)


def test_no_banned_word_is_shown():
	found = [f"  {module} {path.name}: {said}" for module, path, text in _read() for said in banned_said(text)]
	assert not found, "A word we never show (docs/WORDING.md):\n" + "\n".join(found)


def test_the_wording_rules_catch_their_examples():
	assert len(unplain_description("x.y", "We keep it — see: " + "a" * 130)) == 4
	assert not unplain_description("x.y", "Example: 30 days")
	note = "a" * 71
	assert unplain_on_screen(f'__("Its Items"); __("Saved; sent"); note: __("{note}")') == ["Its Items", "Saved; sent", f"note too long: {note}"]
	assert not unplain_on_screen('__("Approve"); __("Total: {0}")')
	assert chatty('_("It doesn\'t read any more")') and not chatty('_("Saved")')
	assert len(commit_like("a.b", "Our press " + "x" * 130)) == 3 and not commit_like("a.b", "Zero means unlimited")
	spec = {"doctype": "DocType", "description": "Its logo comes from here", "fields": [{"fieldname": "f", "description": "Leave empty to use the default"}]}
	assert reasoned(spec) == [("[doctype]", "Its logo comes from here")]
	assert not reasoned({**spec, "doctype": "Report"})
	assert long_headings('title: __("One two three four five six"), label: __("Short")') == ["One two three four five six"]
	assert banned_said('__("Simply save"), __("Save")') == ["Simply save"]
	nodes = tree.nodes('f = {"fieldtype": "Select", "label": _("The Old App Has"), "options": [{"label": "Is Group"}]}\n')
	assert python_labels(nodes) == ["The Old App Has", "Is Group"]
	assert desk_labels('{ fieldtype: "Data", label: __("What Was Billed") }, { value: 1, label: __("Net") }') == ["What Was Billed", "Net"]
	assert select_options([{"fieldtype": "Select", "options": "Open\nThe Old One"}, {"fieldtype": "Data", "options": "x"}]) == ["Open", "The Old One"]
	assert [label for label in ("What Was Billed", "Net", "The Old One") if sentence(label)] == ["What Was Billed", "The Old One"]
