import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("agent", ROOT / "deploy" / "server" / "agent.py")
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


def test_a_moved_site_keeps_its_own_keys_and_comes_back_on():
	old = {"encryption_key": "k", "db_name": "old", "one_token": "t", "maintenance_mode": 1, "pause_scheduler": 1}
	new = {"db_name": "new", "encryption_key": "other"}
	made = agent.merged_config(old, new)
	assert made["encryption_key"] == "k" and made["one_token"] == "t" and made["db_name"] == "new"
	assert "maintenance_mode" not in made and "pause_scheduler" not in made


def test_a_suspended_site_stays_stopped_after_a_move():
	made = agent.merged_config({"maintenance_mode": 1, "pause_scheduler": 1, "db_name": "old"}, {"db_name": "new"}, quiet=True)
	assert made["maintenance_mode"] == 1 and made["pause_scheduler"] == 1 and made["db_name"] == "new"


def test_an_instruction_is_only_believed_when_signed():
	assert agent.signature("s", "body") == agent.signature("s", "body") != agent.signature("other", "body")
