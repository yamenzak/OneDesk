"""A file dropped on the panel, and what a model may be handed of it.

Two rules. The bytes are read on the workspace, as the person asking, so a file
they may not open is a file the model is never given. And only the newest turn
carries them: the conversation goes whole every round, so an attachment on a
five-round run would otherwise be sent five times.
"""

import ast
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

FILES = tree.APP / "one_ai" / "files.py"
CHAT = tree.APP / "one_ai" / "chat.py"
ACTIONS = tree.APP / "one_admin" / "actions.py"
GATEWAY = tree.APP / "one_admin" / "gateway.py"
CAPABILITY = tree.APP / "one_admin" / "capability.py"


def spoken(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


def can_read():
	"""`capability.can_read` without frappe — it touches nothing but its tables."""
	body = ast.parse(CAPABILITY.read_text(encoding="utf-8"))
	wanted = [
		node
		for node in body.body
		if (isinstance(node, ast.FunctionDef) and node.name == "can_read")
		or (isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("READS", "PDF_FROM"))
	]
	room: dict = {}
	exec(compile(ast.Module(body=wanted, type_ignores=[]), str(CAPABILITY), "exec"), room)
	return room["can_read"]


# ------------------------------------------------ what a model may be handed


@pytest.mark.parametrize(
	"model,mime,allowed",
	[
		({"provider": "workers-ai", "reads_image": 1}, "image/png", True),
		({"provider": "workers-ai", "reads_image": 0}, "image/png", False),
		# A PDF is read by the same eyes as a picture, and by Google alone:
		# Workers AI's vision models take an image and answer `Bad input` to a
		# document.
		({"provider": "google-ai-studio", "reads_image": 1}, "application/pdf", True),
		({"provider": "workers-ai", "reads_image": 1}, "application/pdf", False),
		({"provider": "google-ai-studio", "reads_audio": 1}, "audio/mpeg", True),
		({"provider": "google-ai-studio", "reads_image": 1}, "text/csv", False),
	],
)
def test_a_model_is_only_handed_what_it_reads(model, mime, allowed):
	assert can_read()(model, mime) is allowed


def test_the_refusal_happens_before_anything_is_reserved():
	"""A provider refusing an attachment is a 400 after the hold is taken and a
	sentence nobody outside this file could have written."""
	said = spoken(ACTIONS, "run")
	assert said.index("_may_read") < said.index("gateway.call")
	assert "capability.can_read" in spoken(ACTIONS, "_may_read")


# --------------------------------------------------------- whose bytes these are


def test_the_bytes_are_read_as_the_person_asking():
	"""On the workspace, with a permission check, because the account cannot
	read a workspace's disk and should not be able to."""
	said = spoken(FILES, "_held")
	assert "check_permission" in said
	assert "MOST_BYTES" in said


def test_only_the_newest_turn_carries_its_bytes():
	"""The conversation is sent whole every round, so an attachment on a
	five-round run would otherwise go five times."""
	said = spoken(FILES, "carried")
	assert "range(len(turns) - 1, -1, -1)" in said, "not the newest turn"
	assert said.count("_bytes(") == 1


def test_a_conversation_row_never_holds_a_base64():
	"""A row holding every attachment it ever carried is a row that grows until
	it cannot be read — and `described` is what goes into a turn."""
	said = spoken(FILES, "described")
	assert "data" not in said
	for key in ("'name'", "'url'", "'type'", "'size'"):
		assert key in said

	# And what goes back to the panel drops it too, in case one ever survives.
	assert "key != 'data'" in spoken(CHAT, "shown")


def test_each_provider_is_handed_a_file_its_own_way():
	source = GATEWAY.read_text(encoding="utf-8")
	assert "inline_data" in source, "google takes inline_data"
	assert "image_url" in source, "openai's dialect takes a data url"
