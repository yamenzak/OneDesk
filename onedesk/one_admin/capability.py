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

#: What each provider's own word for a model says it **produces** and what it
#: **reads**. Two facts rather than one, because one word was wrong: Gemini
#: Flash was filed as text generation while its own price page lists input rates
#: for text, images, audio and video.
#:
#: Cloudflare says this exactly, in `task.name`, and it is the better of the two
#: signals.
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

#: Google says what a model may be *called* with rather than what it does, which
#: is a much weaker signal — `generateContent` is the general one and covers
#: reading pictures as well as writing text. So it only sets a floor, and the
#: published rates raise it.
A_METHOD = {
	"embedcontent": ("embedding", {"text"}),
	"batchembedcontents": ("embedding", {"text"}),
	"predictlongrunning": ("video", {"text", "image"}),
	"predict": ("image", {"text"}),
	"bidigeneratecontent": ("audio", {"text", "audio"}),
	"generatecontent": ("text", {"text"}),
}

#: The one word a list shows, derived from the two facts above. Nothing is
#: stored that a person maintains: an action asks for a capability and the
#: picker filters on `reads_*` and this together.
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
