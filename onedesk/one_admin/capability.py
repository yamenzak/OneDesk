"""What a model does, which is two facts rather than one word.

Pure, like `prices.py` beside it: this decides which models an action is
allowed to pick from. A model carries what it makes and what it can be fed.
"""

A_TASK = {
	"text generation": ("text", {"text"}),
	"image-to-text": ("text", {"text", "image"}),
	"image classification": ("text", {"image"}),
	"object detection": ("text", {"image"}),
	"text-to-image": ("image", {"text"}),
	"image-to-image": ("image", {"text", "image"}),
	"automatic speech recognition": ("text", {"audio"}),
	"text-to-speech": ("audio", {"text"}),
	"text embeddings": ("embedding", {"text"}),
	"translation": ("translation", {"text"}),
	"summarization": ("text", {"text"}),
	"text classification": ("classification", {"text"}),
}

A_METHOD = {
	"embedcontent": ("embedding", {"text"}),
	"batchembedcontents": ("embedding", {"text"}),
	"predictlongrunning": ("video", {"text", "image"}),
	"predict": ("image", {"text"}),
	"bidigeneratecontent": ("audio", {"text", "audio"}),
	"generatecontent": ("text", {"text"}),
}

def named(produces: str, reads: set[str]) -> str:
	if produces == "embedding":
		return "Embedding"
	if produces == "image":
		return "Image Generation"
	if produces == "video":
		return "Video Generation"
	if produces == "audio":
		return "Audio Generation"
	if produces == "translation":
		return "Translation"
	if produces == "classification":
		return "Text Classification"
	if produces != "text":
		return "Other"

	others = reads - {"text"}
	if len(others) >= 2:
		return "Multimodal"
	if others & {"image", "video"}:
		return "Vision"
	if "audio" in others:
		return "Transcription"
	return "Text Generation"


COVERS = {
	"Text Generation": {"Text Generation", "Vision", "Multimodal"},
	"Vision": {"Vision", "Multimodal"},
	"Transcription": {"Transcription", "Multimodal"},
	"Multimodal": {"Multimodal"},
	"Image Generation": {"Image Generation"},
	"Video Generation": {"Video Generation"},
	"Audio Generation": {"Audio Generation"},
	"Embedding": {"Embedding"},
	"Translation": {"Translation"},
	"Text Classification": {"Text Classification"},
}

WORDS = tuple(COVERS)


def covers(needed: str) -> set[str]:
	"""The model capabilities that can answer an action needing this one."""
	return COVERS.get(needed) or set()


def able(model_says: str, action_needs: str) -> bool:
	return model_says in covers(action_needs)


READS = {
	"image": "reads_image",
	"audio": "reads_audio",
	"video": "reads_video",
	"application/pdf": "reads_image",
}

PDF_FROM = ("google-ai-studio",)


def can_read(model: dict, mime: str) -> bool:
	"""Whether this model may be handed a file of this kind.

	`model` is the row's own fields — `provider` and the four `reads_*` flags —
	so this stays a decision about a model rather than about a doctype.
	"""
	wanted = READS.get(mime) or READS.get((mime or "").split("/")[0])
	if not wanted or not model.get(wanted):
		return False
	if mime == "application/pdf" and model.get("provider") not in PDF_FROM:
		return False
	return True
