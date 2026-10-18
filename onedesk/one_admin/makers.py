"""Who made a model, who runs it, and what to call it. Pure, so the guard in
tests/guards/test_legal.py can read it without Frappe.

The provider runs the model and is a subprocessor; the maker trained it and
its logo is the one shown. A provider missing from `PROVIDERS` is never offered.
"""

from urllib.parse import quote

PROVIDERS = {
	"google-ai-studio": "Google LLC",
	"workers-ai": "Cloudflare, Inc.",
}

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


LOUD = {"it", "fp8", "fp16", "awq", "er", "oss", "glm", "gpt", "ai", "vl", "moe"}

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
