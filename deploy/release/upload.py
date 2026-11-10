"""A release's archive into the registry, with what it holds beside it: the
four commits, the archive's checksum and the box's agent of that commit. Run
by build.sh."""

import json
import os
import sys
from pathlib import Path

import boto3


def main(archive: str, onedesk: str, frappe: str, erpnext: str, hrms: str) -> None:
	bucket = os.environ["R2_ASSETS_BUCKET"]
	store = boto3.client(
		"s3",
		endpoint_url=os.environ["R2_ENDPOINT"],
		region_name="auto",
		aws_access_key_id=os.environ["R2_ASSETS_KEY"],
		aws_secret_access_key=os.environ["R2_ASSETS_SECRET"],
	)
	key = f"releases/{onedesk}"
	store.upload_file(archive, bucket, f"{key}.tar.gz")
	store.upload_file(str(Path(__file__).resolve().parents[1] / "server" / "agent.py"), bucket, f"{key}.agent.py")
	about = {
		"onedesk": onedesk,
		"frappe": frappe,
		"erpnext": erpnext,
		"hrms": hrms,
		"sha256": Path(f"{archive}.sha256").read_text().strip(),
		"size": Path(archive).stat().st_size,
	}
	store.put_object(Bucket=bucket, Key=f"{key}.json", Body=json.dumps(about).encode(), ContentType="application/json")
	print(json.dumps(about))


if __name__ == "__main__":
	main(*sys.argv[1:])
