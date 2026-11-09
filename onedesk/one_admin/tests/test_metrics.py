from botocore.exceptions import ClientError

from onedesk.one_admin import faults, metrics


def test_a_source_that_says_no_is_told_from_one_that_cannot_answer():
	denied = ClientError({"Error": {"Code": "AccessDeniedException"}}, "GetInstanceMetricData")
	assert metrics.why(denied) == metrics.REFUSED
	assert metrics.why(faults.Refused("no", 403)) == metrics.REFUSED
	assert metrics.why(faults.Again("down", 502)) == metrics.UNREACHABLE
	assert metrics.why(TimeoutError()) == metrics.UNREACHABLE


def test_a_source_that_fails_gives_its_state_and_nothing_else():
	def boom():
		raise faults.Refused("no", 403)

	assert metrics._source(boom) == {"state": metrics.REFUSED, "data": None}
	assert metrics._source(lambda: [1]) == {"state": metrics.OK, "data": [1]}


def test_pilot_points_become_busy_cpu_and_a_share_of_memory():
	history = {"system": {"memory_total_bytes": 200, "points": [{"time": 1, "Busy User": 10, "Busy System": 5, "Busy IOWait": 1, "Busy IRQ": None, "Busy Other": 2, "Used": 50, "Root Disk": 40}]}}
	row = metrics.system_rows(history)[0]
	assert (row["cpu"], row["memory"], row["disk"]) == (18, 25, 40)
	assert metrics.system_rows({}) == []


def test_lightsail_metrics_meet_by_their_moment():
	rows = metrics.by_time({"cpu": [(2, 9.0), (1, 8.0)], "burst": [(2, 90.0)]})
	assert rows == [{"time": 1, "cpu": 8.0}, {"time": 2, "cpu": 9.0, "burst": 90.0}]
	assert metrics.latest(rows, "burst") == 90.0


def test_lightsail_bytes_become_bytes_a_second():
	assert metrics.per_second([{"time": 1, "read": 600, "burst": 80}], 300) == [{"time": 1, "read": 2.0, "burst": 80}]


def test_a_card_reads_lightsail_for_cpu_only_when_pilot_gave_nothing():
	system = [{"cpu": 5, "memory": 50, "disk": 40}]
	assert metrics.card_series(system, [{"cpu": 9, "burst": 70}])["cpu"] == [5]
	series = metrics.card_series([], [{"cpu": 9, "burst": 70}])
	assert series["cpu"] == [9] and series["memory"] == [] and series["burst"] == 70


def test_thin_keeps_the_newest_reading_and_the_limit():
	assert metrics.thin([1, 2], 5) == [1, 2]
	kept = metrics.thin(list(range(100)), 10)
	assert len(kept) == 10 and kept[-1] == 99


def test_requests_are_counted_per_workspace_and_strangers_are_left_out():
	groups = [
		{"count": 3, "sum": {"edgeResponseBytes": 9}, "dimensions": {"clientRequestHTTPHost": "acme.t.x"}},
		{"count": 7, "sum": {"edgeResponseBytes": 1}, "dimensions": {"clientRequestHTTPHost": "bold.t.x"}},
		{"count": 50, "dimensions": {"clientRequestHTTPHost": "other.y"}},
	]
	tenants = {"acme": {"name": "Acme", "server": "se-1"}, "bold": {"name": "Bold", "server": "se-2"}}
	rows = metrics.requests_by_workspace(groups, "t.x", tenants)
	assert [(one["workspace"], one["requests"]) for one in rows] == [("Bold", 7), ("Acme", 3)]


def test_a_bucket_keeps_what_it_holds_and_how_often_it_was_asked():
	account = {
		"r2StorageAdaptiveGroups": [{"max": {"payloadSize": 8, "objectCount": 2}, "dimensions": {"bucketName": "files"}}],
		"r2OperationsAdaptiveGroups": [{"sum": {"requests": 4}, "dimensions": {"bucketName": "files"}}, {"sum": {"requests": 1}, "dimensions": {"bucketName": "new"}}],
	}
	found = {one["bucket"]: one for one in metrics.buckets(account)}
	assert found["files"]["requests"] == 4 and found["files"]["size"] == 8 and found["new"]["objects"] == 0
