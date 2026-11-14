"""What the release build publishes (deploy/release/upload.py) and how
OneAdmin hears of it (releases.released)."""

import importlib.util
import sys
from pathlib import Path

from onedesk.one_admin import releases

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("upload", ROOT / "deploy" / "release" / "upload.py")
upload = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(upload)


def test_the_template_shares_nothing_a_site_must_hold_alone():
	config = {
		"db_name": "_a",
		"db_password": "p",
		"encryption_key": "k",
		"admin_password": "x",
		"pilot_auth_token": "t",
		"onedesk_vapid_private": "v",
		"host_name": "h",
		"one_mail_secret": "s",
		"maintenance_mode": 1,
		"max_file_size": 10,
		"server_script_enabled": 1,
	}
	assert upload.shareable(config) == {"max_file_size": 10, "server_script_enabled": 1}


def test_the_workflow_and_the_admin_sign_alike():
	assert upload.signed("s", "body") == releases.servers.signed("s", "body")


def test_a_release_call_is_only_believed_while_it_is_fresh():
	assert releases.fresh(1000, 1000 + releases.FRESH_FOR)
	assert not releases.fresh(1000, 1001 + releases.FRESH_FOR)
	assert not releases.fresh("1000", 1000)
	assert not releases.fresh(None, 1000)


def test_a_release_lists_each_private_app_as_its_manifest_says_without_running_it(tmp_path):
	app = tmp_path / "private" / "acme" / "acme"
	app.mkdir(parents=True)
	(app / "hooks.py").write_text('import os\nos.remove("/")\n')
	(app / "manifest.py").write_text('import os\nos.remove("/")\nAPP = App(id="acme", name="Acme Fleet", kind="app", module="Acme", line=_lt("Acme\'s vans."), mark="truck")\n')
	(tmp_path / "private" / "loose").mkdir()
	(tmp_path / "private" / "loose" / "manifest.py").write_text('APP = App(id="loose", name="Loose", module="Loose")\n')
	plain = tmp_path / "private" / "plain" / "plain"
	plain.mkdir(parents=True)
	(plain / "hooks.py").write_text('app_name = "plain"\n')
	assert upload.declared(tmp_path) == [{"app": "acme", "title": "Acme Fleet", "said": "Acme's vans.", "icon": "truck"}]


def test_every_private_app_here_declares_itself():
	names = sorted(path.name for path in (ROOT / "private").iterdir() if (path / path.name / "manifest.py").exists())
	assert names and [one["app"] for one in upload.declared()] == names
	assert all(one["title"] != one["app"] and one["said"] and one["icon"] for one in upload.declared())


DEMO_SPEC = importlib.util.spec_from_file_location("demo", ROOT / "deploy" / "release" / "demo.py")
demo = importlib.util.module_from_spec(DEMO_SPEC)
DEMO_SPEC.loader.exec_module(demo)
SHA = "abc123"


def _built(out, with_demo: bool, checked: bool = True):
	for name in (f"{SHA}.tar.gz", f"{SHA}.bench.tar.gz", f"{SHA}.site.tar.gz", *([demo.name(SHA)] if with_demo else [])):
		(out / name).write_bytes(b"x" * 10)
		if checked or name != demo.name(SHA):
			(out / f"{name}.sha256").write_text(f"sum-{name}\n")
	(out / f"{SHA}.bench.python").write_text(".local/share/uv/python\n")


def test_the_ready_demo_sits_beside_the_template_under_the_same_name():
	assert demo.name(SHA) == f"{SHA}.demo.tar.gz"
	assert demo.name(SHA).removesuffix(demo.SUFFIX) == f"{SHA}.site.tar.gz".removesuffix("site.tar.gz")


def test_a_ready_demo_over_its_budget_is_left_out():
	assert demo.over_budget(demo.BUDGET_MB * 1024 * 1024) is None
	assert "over its budget" in demo.over_budget(demo.BUDGET_MB * 1024 * 1024 + 1)
	assert demo.over_budget(2 * 1024 * 1024, budget_mb=1)


def test_a_release_puts_up_its_ready_demo_only_when_the_build_made_and_checked_one(tmp_path):
	_built(tmp_path, with_demo=False)
	assert upload.parts(tmp_path, SHA) == list(upload.PARTS)
	_built(tmp_path, with_demo=True, checked=False)
	assert demo.SUFFIX not in upload.parts(tmp_path, SHA), "an archive with no checksum is a demo the build did not finish"
	_built(tmp_path, with_demo=True)
	assert upload.parts(tmp_path, SHA)[-1] == demo.SUFFIX


def test_a_dry_run_says_what_it_would_put_up_and_touches_nothing(tmp_path, monkeypatch):
	_built(tmp_path, with_demo=True)
	monkeypatch.delenv("R2_ASSETS_BUCKET", raising=False)
	monkeypatch.setitem(sys.modules, "boto3", None)
	keys = upload.publish(str(tmp_path), SHA, "f", "e", "h", dry_run=True)
	assert keys == [f"releases/{SHA}.tar.gz", f"releases/{SHA}.bench.tar.gz", f"releases/{SHA}.site.tar.gz", f"releases/{SHA}.demo.tar.gz", f"releases/{SHA}.agent.py", f"releases/{SHA}.json"]
	described = upload.about(tmp_path, SHA, "f", "e", "h")
	assert described["demo"] == {"sha256": f"sum-{demo.name(SHA)}", "size": 10}
	(tmp_path / demo.name(SHA)).unlink()
	assert "demo" not in upload.about(tmp_path, SHA, "f", "e", "h"), "a release without one says so by leaving it out"


def test_the_build_has_a_dry_run_and_builds_the_demo_in_its_own_step():
	build = (ROOT / "deploy" / "release" / "build.sh").read_text()
	flow = (ROOT / ".github" / "workflows" / "release-assets.yml").read_text()
	assert "--dry-run) PUBLISH=false" in build and '[ "${PUBLISH:-true}" = true ] || dry="--dry-run"' in build
	assert build.index("build_stage\n\t\tdemo_stage\n\t\tpublish_stage") > build.index("demo_stage() {")
	assert 'emptied "$demo_site"' in build and "onedesk.one_demo.build.load" in build, "the demo is built as a session builds it, then emptied as the template is"
	assert build.index('emptied "$demo_site"') < build.index('packed "$bench/sites/$demo_site"')
	assert flow.index("build.sh build") < flow.index("build.sh demo") < flow.index("build.sh publish") < flow.index("Keep the template")
	step = flow[flow.index("name: Demo database") : flow.index("name: Publish")]
	assert "continue-on-error: true" in step and "R2_" not in step, "a failed demo leaves the release without one, and the demo step holds no key"
