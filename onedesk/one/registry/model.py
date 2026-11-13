"""What an app, a centre or an engine says about itself in its manifest.py
(docs/run/RUN.md, OneRegistry). Pure: nothing here imports frappe, so the
guards, the scripts and hooks.py read it without a site."""

from dataclasses import dataclass, field

KINDS = ("app", "centre", "engine")


def _lt(text: str) -> str:
	"""Marks a word the interface shows; the renderer says it in the reader's
	language. Plain here, so a manifest reads without frappe."""
	return text


UI = ("native", "bespoke", "mixed", "none")
"""How an app's screens are made: native, frappe's own lists and forms but
for its regions (an app on ERPNext or HRMS); bespoke, every screen One's own,
built from frappe's and frappe-ui's parts; mixed, both, each screen saying
which by its regions; none, a centre's or an engine's, which have no app
screens."""
REGIONS = ("page",)
"""What a region is: a desk page One draws (an island, a home, a console)."""
COUNTRY = ("built", "works", "not checked")


@dataclass(frozen=True)
class Roles:
	"""frappe's roles a level gives in this app: User's, then Manager's on top."""

	user: tuple[str, ...] = ()
	manager: tuple[str, ...] = ()


@dataclass(frozen=True)
class Kept:
	"""Why the app can't be turned off once it holds records, and the dotted
	path of a function that says whether it holds them now; none means it is
	never offered as a switch at all. An app is kept when other apps' records
	need its records, or the law needs them reachable."""

	why: str
	held: str = ""


@dataclass(frozen=True)
class Region:
	"""A place an app on ERPNext or HRMS is drawn by One rather than by frappe:
	a screen (a page, an island) or a part of frappe's own (a record type's
	head, its list's states). Everything else in a native app is frappe's."""

	kind: str
	name: str
	why: str


@dataclass(frozen=True)
class Settle:
	"""A function that makes the site right for the app, relative to its
	folder ("access.settle"): run when the app is installed and again on every
	migrate, or only at install (`install_only`). `last` runs it after every
	app's other steps, for what reads them all."""

	path: str
	install_only: bool = False
	last: bool = False


@dataclass(frozen=True)
class App:
	"""One folder of One: an app people use, a centre they open, or an engine
	the others stand on. `id` is the folder and never changes; `name` is what
	people see and can change in one place. `names` are the stems of its files
	that still sit outside its folder (public/, frontend/src/). `parts` are its
	sub-packages that carry centre parts of their own (OneAI's reading);
	`hooks` names, relative to the folder, what a hook takes from it beyond
	what its files declare by convention (registry/hooks.py)."""

	id: str
	name: str
	kind: str
	module: str
	line: str = ""
	mark: str = ""
	owns: tuple[str, ...] = ()
	rail: int | None = None
	sidebar: str | None = None
	roles: Roles = Roles()
	needs: tuple[str, ...] = ()
	kept: Kept | None = None
	private: bool = False
	ui: str = "none"
	regions: tuple[Region, ...] = ()
	screens: str | None = None
	names: tuple[str, ...] = ()
	help: tuple[tuple[str, str], ...] = ()
	countries: dict[str, str] = field(default_factory=dict)
	plan: tuple[str, ...] = ()
	ready: dict = field(default_factory=dict)
	interface: dict = field(default_factory=dict)
	companies: tuple[str, ...] = ()
	windowless: str = ""
	no_roles: str = ""
	operators: bool = False
	frontend: str | None = None
	parts: tuple[str, ...] = ()
	hooks: dict[str, tuple[str, ...]] = field(default_factory=dict)
	settle: tuple[Settle, ...] = ()
	centres: tuple[str, ...] = ()
	makes: tuple[str, ...] = ()
