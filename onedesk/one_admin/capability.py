"""What a model does, which is two facts rather than one word.

Pure, like `prices.py` beside it, and for a related reason: this decides which
models an action is allowed to pick from, and getting it wrong is a picker that
offers a transcriber for a job that needs eyes.

**One word was wrong.** The first version of this filed `gemini-2.5-flash-lite`
as text generation because that is what its API said it could be called with,
while its own published price list carries input rates for text, pictures, sound
and video. So a model now carries what it *makes* and what it can be *fed*, the
second is a set, and the one word on the list is derived from both.
"""

#: Cloudflare's `task.name`, which says plainly what a model does and is the
#: better of the two providers' signals.
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
	"translation": ("text", {"text"}),
	"summarization": ("text", {"text"}),
	"text classification": ("text", {"text"}),
}

#: Google says what a model may be *called* with rather than what it does, so
#: this only sets a floor and the published rates raise it.
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
		# Speech and music are both audio out, and neither provider says which.
		# One word that is true beats two where one is guessed.
		return "Audio Generation"
	if produces != "text":
		return "Other"

	# What it can be fed, beyond the obvious. A model that reads two of pictures,
	# sound and video is not a transcriber that happens to see, and calling it
	# one was the thing wrong with the first version of this: `gemini-2.5-flash-lite`
	# publishes input rates for all four and came out as "Transcription".
	others = reads - {"text"}
	if len(others) >= 2:
		return "Multimodal"
	if others & {"image", "video"}:
		return "Vision"
	if "audio" in others:
		return "Transcription"
	return "Text Generation"


#: Which capabilities cover which. A model that reads more than a job needs can
#: still do the job; one that reads less cannot. Written down rather than worked
#: out, because "may this model do this job" is a decision, and a table of them
#: is a thing somebody can read and disagree with.
COVERS = {
	# Not Transcription: a model that reads sound and nothing else cannot answer
	# a job that hands it text, however much text it writes back. Caught by
	# offering whisper and watching it turn up as a candidate summariser.
	"Text Generation": {"Text Generation", "Vision", "Multimodal"},
	"Vision": {"Vision", "Multimodal"},
	"Transcription": {"Transcription", "Multimodal"},
	"Multimodal": {"Multimodal"},
	"Image Generation": {"Image Generation"},
	"Video Generation": {"Video Generation"},
	"Audio Generation": {"Audio Generation"},
	"Embedding": {"Embedding"},
}

#: Every word a model or an action may carry, so a Select option added to one
#: and not the other fails a guard rather than a picker.
WORDS = tuple(COVERS)


def covers(needed: str) -> set[str]:
	"""The model capabilities that can answer an action needing this one."""
	return COVERS.get(needed) or set()


def able(model_says: str, action_needs: str) -> bool:
	return model_says in covers(action_needs)
