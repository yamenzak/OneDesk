from onedesk.one_admin import boxes, servers


def test_the_next_box_takes_the_lowest_free_number():
	assert servers.next_name([], "eu-north-1") == "se-1"
	assert servers.next_name(["se-1", "se-3"], "eu-north-1") == "se-2"


def test_a_box_answers_for_its_addresses_and_nothing_else():
	rules = boxes.ingress(["a.x", "*.d.x"])
	assert rules[0] == {"hostname": "a.x", "service": "http://localhost:80"} and rules[-1] == {"service": "http_status:404"}


def test_the_run_token_asks_only_for_what_a_server_needs():
	groups = [{"name": name, "id": name, "scopes": [scope]} for name, scope in boxes.NEEDS]
	made = boxes.wanted_policies(groups, "acct")
	assert sorted(one["id"] for policy in made for one in policy["permission_groups"]) == sorted(name for name, _ in boxes.NEEDS)


def test_a_server_is_called_down_once_and_back_once():
	assert servers.after_a_check(0, False) == (1, None)
	assert servers.after_a_check(1, False) == (2, None)
	assert servers.after_a_check(2, False) == (3, "down")
	assert servers.after_a_check(3, False) == (4, None), "said once"
	assert servers.after_a_check(4, True) == (0, "back")
	assert servers.after_a_check(1, True) == (0, None), "a blip is not news"


def test_a_dropped_bench_is_cleared_and_nothing_else():
	found = [{"domain": "pilot-se-1-r0123abcd.x"}, {"domain": "pilot-se-1-r89abcdef.x"}, {"domain": "pilot-se-1.x"}, {"domain": "pilot-se-12-r0123abcd.x"}, {"domain": "a.x"}]
	assert boxes.stale_benches(found, "domain", "se-1", ["pilot-se-1.x", "pilot-se-1-r89abcdef.x"]) == [{"domain": "pilot-se-1-r0123abcd.x"}]


class _Cloudflare(boxes.Cloudflare):
	def __init__(self, apps):
		super().__init__("acct", "token")
		self.apps, self.deleted = apps, []

	def call(self, method, path, token=None, **kwargs):
		if method == "DELETE":
			self.deleted.append(path.rsplit("/", 1)[-1])
			return {}
		if path.endswith("/access/apps"):
			page = kwargs["params"]["page"]
			return {"result": self.apps[page - 1], "result_info": {"total_pages": len(self.apps)}}
		return {"result": []}


def test_a_removed_server_loses_every_bench_lock_on_every_page():
	cloudflare = _Cloudflare([[{"id": "box", "domain": "pilot-se-1.x"}, {"id": "a", "domain": "pilot-se-1-r0123abcd.x"}], [{"id": "b", "domain": "pilot-se-1-r89abcdef.x"}, {"id": "other", "domain": "pilot-se-2-r0123abcd.x"}]])
	cloudflare.forget("one-se-1", "t", "pilot-se-1.x", [])
	assert cloudflare.deleted == ["box", "a", "b", "t"]


def test_a_dropped_bench_leaves_the_tunnel_and_its_lock_goes():
	cloudflare = _Cloudflare([[{"id": "gone", "domain": "pilot-se-1-r0123abcd.x"}, {"id": "kept", "domain": "pilot-se-1-r89abcdef.x"}]])
	cloudflare.drop_bench("one-se-1", "t", ["pilot-se-1.x", "pilot-se-1-r89abcdef.x"], "x")
	assert cloudflare.deleted == ["gone"]
