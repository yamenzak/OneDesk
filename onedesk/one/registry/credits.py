"""The kinds of use a workspace is charged OneCredits for, declared once:
each kind's id, the same as its markup's in one_admin/price_list.py
(`MARKUP`), and what OneMarketplace says it costs. An app's manifest names
the kinds it uses (`credits=`), and the registry refuses one that is not
here. Words that name an app say it as `{oneos}`, filled from the registry.
Pure."""

from dataclasses import dataclass

from onedesk.one.registry.model import _lt


@dataclass(frozen=True)
class Use:
	id: str
	said: str


USES = (
	Use("ai", _lt("Each answer, each document read and each piece of work done by an agent uses credits, by how much the model reads and writes.")),
	Use("oneos", _lt("Opening a file in {oneos} uses credits for each minute it is open.")),
	Use("office", _lt("Turning a Word, Excel or PowerPoint file into a PDF uses credits for the seconds it takes.")),
	Use("mail", _lt("Each mail sent from a workspace address uses one credit.")),
)

IDS = tuple(one.id for one in USES)


def get(id: str) -> Use:
	for one in USES:
		if one.id == id:
			return one
	raise KeyError(id)


def unknown(ids) -> list[str]:
	"""The ids among these that no kind of use has."""
	return [one for one in ids if one not in IDS]
