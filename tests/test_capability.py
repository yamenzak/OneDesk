"""What a model does, read back without a site.

The failure this guards is the one that was actually in the code: a multimodal
model filed as text generation, which is a picker that hides every model that
can see from the action that needs one.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree


def _capability():
	import importlib.util

	at = tree.APP / "one_admin" / "capability.py"
	spec = importlib.util.spec_from_file_location("onedesk_capability", at)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


capability = _capability()


def test_the_module_has_no_frappe_in_it():
	import ast

	body = ast.parse((tree.APP / "one_admin" / "capability.py").read_text(encoding="utf-8"))
	for node in ast.walk(body):
		if isinstance(node, ast.Module | ast.FunctionDef):
			node.body = [
				n
				for n in node.body
				if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
			]
	assert "frappe" not in ast.unparse(body)


@pytest.mark.parametrize(
	"produces,reads,word",
	[
		# The one that was wrong. Gemini Flash publishes input rates for all
		# four and was filed as text generation.
		("text", {"text", "image", "audio", "video"}, "Multimodal"),
		("text", {"text", "image"}, "Vision"),
		("text", {"text", "video"}, "Vision"),
		("text", {"audio"}, "Transcription"),
		("text", {"text"}, "Text Generation"),
		("image", {"text"}, "Image Generation"),
		("video", {"text", "image"}, "Video Generation"),
		("audio", {"text"}, "Audio Generation"),
		("embedding", {"text", "image", "audio", "video"}, "Embedding"),
		("", set(), "Other"),
	],
)
def test_the_one_word_is_derived_from_the_two_facts(produces, reads, word):
	assert capability.named(produces, reads) == word


def test_a_model_that_reads_two_things_is_not_a_transcriber_that_sees():
	"""Order matters here, and getting it wrong is what filed a model that reads
	pictures, sound and video under the narrowest of the three."""
	assert capability.named("text", {"text", "image", "audio"}) == "Multimodal"
	assert capability.named("text", {"audio"}) == "Transcription"


def test_both_providers_words_are_read_as_two_facts():
	for table in (capability.A_TASK, capability.A_METHOD):
		assert table, "a lookup with nothing in it maps everything to Other"
		for said, (produces, reads) in table.items():
			assert produces, f"{said} says nothing about what it makes"
			assert isinstance(reads, set) and reads, f"{said} says nothing about what it reads"


def test_cloudflares_word_is_the_more_specific_of_the_two():
	"""It says what the model does. Google says what it may be called with, and
	`generateContent` covers reading pictures as well as writing text — which is
	why the rates have to raise the floor it sets."""
	assert capability.A_TASK["image-to-text"] == ("text", {"text", "image"})
	assert capability.A_METHOD["generatecontent"] == ("text", {"text"})

def test_a_translator_is_not_a_chat_model():
	"""Text in, text out, and it cannot hold a conversation. Measured against
	the real models: a reranker, a sentiment classifier and two translators all
	answered `Bad input` to a chat body, having been offered because "produces
	text from text" is exactly what a chat model does too."""
	assert capability.named(*capability.A_TASK["translation"]) == "Translation"
	assert capability.named(*capability.A_TASK["text classification"]) == "Text Classification"
	# And nothing covers them, so an action needing Text Generation cannot pick
	# one — which is how they were being offered in the first place.
	assert "Translation" not in capability.covers("Text Generation")
	assert "Text Classification" not in capability.covers("Text Generation")
	assert capability.covers("Translation") == {"Translation"}
