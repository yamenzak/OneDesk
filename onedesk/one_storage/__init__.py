"""OneCloud's folder before it was renamed one_cloud, kept one release so a
job queued or a scheduler entry from before the update still runs: any
`onedesk.one_storage.<path>` imports `onedesk.one_cloud.<path>`. Not a
module of One: no manifest, not in modules.txt. Removed at P2.9 (docs/run/RUN.md,
D4)."""

import importlib
import importlib.abc
import importlib.util
import sys

MOVED_TO = "onedesk.one_cloud"


class _Moved(importlib.abc.MetaPathFinder, importlib.abc.Loader):
	def find_spec(self, fullname, path=None, target=None):
		if fullname.startswith(__name__ + "."):
			return importlib.util.spec_from_loader(fullname, self)
		return None

	def create_module(self, spec):
		moved = importlib.import_module(MOVED_TO + spec.name[len(__name__) :])
		spec.loader_state = moved.__spec__
		return moved

	def exec_module(self, module):
		module.__spec__ = module.__spec__.loader_state


if not any(isinstance(one, _Moved) for one in sys.meta_path):
	sys.meta_path.insert(0, _Moved())
