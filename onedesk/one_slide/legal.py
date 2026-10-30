"""What OneSlide adds to the agreements: OneAI can design a slide or make a
picture or a video from a description. A presentation is a file in OneCloud,
so what OneCloud's agreements say of a file holds for it. See
one_slide/AGENTS.md and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OneSlide"

clause(
	document="ai",
	section="modules",
	key="oneslide-makes",
	module=M,
	body="""
		In OneSlide, OneAI can design a slide, or make a picture or a short video, from what you describe. It
		is sent only that description and, for a slide, the business's name and colour. What it makes is put
		in the presentation, where it can be changed or deleted like anything else on a slide.
	""",
)
