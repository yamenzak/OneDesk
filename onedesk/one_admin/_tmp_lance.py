import frappe, requests, time
def run():
	s = frappe.get_cached_doc("One Admin Settings")
	account = s.cloudflare_account; token = s.get_password("cloudflare_token", raise_exception=False)
	from onedesk.one_admin import keys
	prefix = keys.prefix("4dl") + "search/"
	c = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{account}/r2/temp-access-credentials",
		headers={"Authorization": f"Bearer {token}"},
		json={"bucket": s.bucket_global, "parentAccessKeyId": s.r2_key_id, "permission": "object-read-write", "prefixes": [prefix], "ttlSeconds": 900}, timeout=20).json()["result"]
	import lancedb
	opts = {"aws_access_key_id": c["accessKeyId"], "aws_secret_access_key": c["secretAccessKey"], "aws_session_token": c["sessionToken"],
		"aws_endpoint": f"https://{account}.r2.cloudflarestorage.com", "aws_region": "auto"}
	uri = f"s3://{s.bucket_global}/{prefix}lance_probe"
	db = lancedb.connect(uri, storage_options=opts)
	db.create_table("probe", data=[{"id": 0, "text": "x", "vector": [0.0, 1.0, 0.5]}], mode="overwrite")
	from concurrent.futures import ThreadPoolExecutor
	def add(i):
		lancedb.connect(uri, storage_options=opts).open_table("probe").add([{"id": i, "text": f"row {i}", "vector": [float(i), 1.0, 0.5]}])
	t0=time.time()
	with ThreadPoolExecutor(6) as ex: list(ex.map(add, range(1,13)))
	fresh = lancedb.connect(uri, storage_options=opts).open_table("probe")
	print("concurrent: rows", fresh.count_rows(), "of 13, secs", round(time.time()-t0,2), "ids", sorted(r["id"] for r in fresh.search().limit(50).to_list()))
	t0=time.time(); add(99); print("one add secs", round(time.time()-t0,2))
	t0=time.time(); fresh.delete("id = 99"); fresh.add([{"id": 99, "text": "y", "vector": [1.0,1.0,0.5]}]); print("delete+add secs", round(time.time()-t0,2))
	db.drop_table("probe")
