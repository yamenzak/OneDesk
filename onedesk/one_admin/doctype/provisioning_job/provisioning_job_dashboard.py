"""What a job wrote in the log: the rungs it moved its workspace to
(one_admin/log.py writes the job on each)."""


def get_data():
	return {
		"fieldname": "job",
		"transactions": [{"label": "Log", "items": ["Tenant Event"]}],
	}
