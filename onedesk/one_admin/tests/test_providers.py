import base64
import json
from pathlib import Path

from onedesk.one_admin import providers

APP = Path(__file__).resolve().parents[2]
ANSWERS = {
	"oracle": ("eu-frankfurt-1\n", "Oracle", "eu-frankfurt-1"),
	"aws": (json.dumps({"accountId": "1", "availabilityZone": "eu-north-1a", "instanceId": "i-0", "region": "eu-north-1"}), "AWS", "eu-north-1"),
	"google": ("projects/123456789/zones/europe-west3-c", "Google Cloud", "europe-west3"),
	"azure": (json.dumps({"location": "westeurope", "name": "vm", "vmSize": "Standard_B2s", "zone": "1"}), "Azure", "westeurope"),
	"digitalocean": ("fra1", "DigitalOcean", "fra1"),
	"hetzner": ("fsn1-dc14", "Hetzner", "fsn1"),
	"vultr": (json.dumps({"hostname": "box", "instanceid": "abc", "region": {"regioncode": "FRA"}}), "Vultr", "fra"),
	"akamai": (json.dumps({"id": 1, "label": "box", "region": "de-fra-2", "type": "g6-standard-2"}), "Akamai", "de-fra-2"),
	"scaleway": (json.dumps({"id": "x", "name": "box", "zone": "fr-par-1", "location": {"zone_id": "par1"}}), "Scaleway", "fr-par-1"),
}


def test_each_cloud_is_known_by_what_its_metadata_service_answers():
	for key, (answer, provider, region) in ANSWERS.items():
		assert providers.where({key: answer}) == (provider, region), key


def test_an_older_scaleway_answer_names_its_zone_under_location():
	assert providers.where({"scaleway": json.dumps({"location": {"zone_id": "par1"}})}) == ("Scaleway", "par1")


def test_a_machine_no_cloud_answers_for_is_other_with_no_region():
	assert providers.where({}) == ("Other", "")
	assert providers.where({"oracle": "<html>Not found</html>", "aws": "{}", "vultr": json.dumps({"region": "FRA"}), "azure": "[1]"}) == ("Other", "")


def test_the_first_cloud_that_answers_sensibly_wins():
	assert providers.where({"oracle": "", "digitalocean": "nyc3", "hetzner": "fsn1-dc14"}) == ("DigitalOcean", "nyc3")


def test_what_the_machine_sends_is_read_from_base64_and_the_rest_dropped():
	sent = {"oracle": base64.b64encode(b"eu-frankfurt-1").decode(), "aws": "not base64!", "google": 5, "hetzner": "A" * (providers.HELD + 4)}
	assert providers.decoded(sent) == {"oracle": "eu-frankfurt-1"}
	assert providers.decoded(None) == {}


def test_every_provider_is_offered_and_has_its_mark():
	doctype = json.loads((APP / "one_admin" / "doctype" / "workspace_server" / "workspace_server.json").read_text())
	offered = next(one["options"] for one in doctype["fields"] if one["fieldname"] == "provider").split("\n")
	assert set(offered) == {provider for _key, provider, _read in providers.READERS} | {providers.OTHER}
	marks = {one["name"] for one in json.loads((APP / "fixtures" / "custom_icon.json").read_text())}
	missing = [one for one in offered if one.lower().replace(" ", "-") not in marks]
	assert not missing, missing
