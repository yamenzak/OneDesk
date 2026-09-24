"""Which language a text is in, from the small words every sentence has.

Good enough to choose how "03/04/2026" and "1.234,56" are read, and to say
which language a letter is in without asking a model. Pure.
"""

import re

COMMON = {
	"de": "der die das und ist nicht mit für von den dem ein eine sie wir ihr bitte sehr zu auf im bei",
	"en": "the and is are not with for from this that you your we our please to of in on at",
	"fr": "le la les et est pas avec pour de des une vous nous votre merci sur dans au",
	"es": "el la los las y es no con para de una usted nosotros gracias por en del su",
	"it": "il la le e è non con per di una voi noi grazie su nel del alla",
	"nl": "de het een en is niet met voor van wij u uw bedankt op in bij",
	"tr": "ve bir bu için ile değil da de size bize teşekkür lütfen olarak",
	"pt": "o a os as e é não com para de uma você nós obrigado em do da",
}
WORDS = {language: set(said.split()) for language, said in COMMON.items()}


def guess(text: str) -> str | None:
	sample = (text or "")[:6000]
	if not sample.strip():
		return None
	letters = [one for one in sample if one.isalpha()]
	if letters and sum(1 for one in letters if "؀" <= one <= "ۿ") > len(letters) * 0.3:
		return "ar"
	words = re.findall(r"[a-zà-ÿğışçöü]+", sample.lower())
	if len(words) < 3:
		return None
	scores = {language: sum(1 for word in words if word in common) for language, common in WORDS.items()}
	best = max(scores, key=scores.get)
	return best if scores[best] >= 2 else None
