"""Who made a model, who runs it, and what to call it. Pure, so the guard in
tests/test_legal.py can read it without Frappe.

Two companies here and they are not the same thing. The **provider** runs the
model and receives what a workspace sends it, so it is a subprocessor and
has to be named in the agreements (one_ai/legal.py). The **maker** trained it
(Meta made Llama, which Cloudflare runs), and is what a person recognises, so
its logo is the one shown.

A provider missing from `PROVIDERS` is never offered to a workspace
(`actions.offered`), whatever the operator switched on in the catalogue: a
model whose company the subprocessors list does not name would send customer
data somewhere the agreements do not say.
"""

from urllib.parse import quote

#: Every provider a workspace's data may go to, and the company that is, as
#: one_ai/legal.py names it.
PROVIDERS = {
	"google-ai-studio": "Google LLC",
	"workers-ai": "Cloudflare, Inc.",
}

#: A maker by the organisation in a Workers AI model's path (its second part):
#: the name a person knows it by, and the domain its logo is fetched for.
MAKERS = {
	"google": ("Google", "gemini.google.com"),
	"meta": ("Meta", "llama.com"),
	"meta-llama": ("Meta", "llama.com"),
	"openai": ("OpenAI", "openai.com"),
	"qwen": ("Qwen", "qwen.ai"),
	"mistralai": ("Mistral AI", "mistral.ai"),
	"mistral": ("Mistral AI", "mistral.ai"),
	"deepseek-ai": ("DeepSeek", "deepseek.com"),
	"moonshotai": ("Moonshot AI", "kimi.com"),
	"zai-org": ("Z.ai", "z.ai"),
	"nvidia": ("NVIDIA", "nvidia.com"),
	"ibm-granite": ("IBM", "ibm.com"),
	"black-forest-labs": ("Black Forest Labs", "bfl.ai"),
	"microsoft": ("Microsoft", "microsoft.com"),
	"baai": ("BAAI", "baai.ac.cn"),
}

#: Whose logo a provider's own models carry.
BY_PROVIDER = {
	"google-ai-studio": ("Google", "gemini.google.com"),
	"workers-ai": ("Cloudflare", "cloudflare.com"),
}


def maker(provider: str, model: str) -> tuple[str, str]:
	"""(name, domain) of whoever made `model`, run by `provider`."""
	parts = model.split("/")
	if model.startswith("@") and len(parts) >= 3:
		org = parts[1].lower()
		if org in MAKERS:
			return MAKERS[org]
	return BY_PROVIDER.get(provider, (provider, ""))


def logo(domain: str, size: int = 64) -> str:
	"""Google's favicon service, v2: a domain's logo, or a globe when it has none."""
	if not domain:
		return ""
	return (
		"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL"
		f"&url={quote('https://' + domain, safe='')}&size={size}"
	)


#: Parts of a model's id that read better in capitals.
LOUD = {"it", "fp8", "fp16", "awq", "er", "oss", "glm", "gpt", "ai", "vl", "moe"}

#: Names their makers spell their own way.
SPELT = {"deepseek": "DeepSeek", "qwq": "QwQ"}


def pretty(label: str) -> str:
	"""A catalogue label as a person would write it. Cloudflare's are ids
	("gemma-4-26b-a4b-it"); Google's are already names and are left alone."""
	if not label or label != label.lower() or " " in label:
		return label
	words = []
	for word in label.replace("_", "-").split("-"):
		if not word:
			continue
		if word in SPELT:
			words.append(SPELT[word])
		elif word in LOUD or _size(word):
			words.append(word.upper())
		elif word[0].isdigit():
			words.append(word)
		else:
			words.append(word[0].upper() + word[1:])
	return " ".join(words)


def _size(word: str) -> bool:
	"""A parameter count: 70b, 1.5b, a4b (active parameters), 8x7b."""
	core = word[1:] if word[0] in "ax" else word
	return len(core) > 1 and core[-1] in "bmk" and core[:-1].replace(".", "").replace("x", "").isdigit()
