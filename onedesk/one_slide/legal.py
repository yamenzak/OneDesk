"""What OneSlide adds to the agreements: OneAI can design a slide or make a
picture or a video from a description, and a font can be added from Google's
catalogue once a workspace turns that on. A presentation is a file in OneCloud,
so what OneCloud's agreements say of a file holds for it. See
one_slide/AGENTS.md and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause, service, subprocessor

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

subprocessor(
	name="Google LLC",
	module=M,
	purpose="Google Fonts, asked for a font family's files when somebody adds that family to the workspace",
	data="The name of the font family asked for, and nothing about the workspace or its people",
	where="The United States and Google's regional endpoints",
	safeguard="Standard Contractual Clauses and Google's data processing terms",
	url="https://cloud.google.com/terms/data-processing-addendum",
	service="google_fonts",
)

service(
	key="google_fonts",
	module=M,
	title="Fonts from Google",
	does="Adds a font family from Google's catalogue to the workspace's fonts, kept in the workspace from then on.",
	sends="The name of the family asked for, by our server, when somebody adds it. Nothing when anyone reads a slide.",
	off="The workspace has the fonts One comes with and those uploaded to it. Fonts already added stay.",
	hosts=("fonts.google.com", "fonts.googleapis.com", "fonts.gstatic.com"),
)

clause(
	document="privacy",
	section="modules",
	key="oneslide-fonts",
	module=M,
	body="""
		A font is a file in the workspace like any other, kept where its other files are. One comes with a set of
		fonts, Arabic among them, served from your workspace. A font from Google's catalogue is fetched once, by our
		server, when somebody adds it. Google is sent only the family's name. Fonts from Google is an optional
		service, off until your workspace's administrators turn it on. Nobody's browser asks Google for a font when
		a slide, a document or a screen is shown.
	""",
)
