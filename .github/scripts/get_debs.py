#!/usr/bin/env python3

import os
import jenkins
import requests

# if os.environ.get("JENKINS_SERVER").endswith("/"):
# 	jenkins_url = os.environ.get("JENKINS_SERVER")[:-1]
# else:
# 	jenkins_url = os.environ.get("JENKINS_SERVER")
jenkins_url = os.environ.get("JENKINS_SERVER")

server = jenkins.Jenkins(
	url=os.environ.get("JENKINS_SERVER"),
	username=os.environ.get("JENKINS_USERNAME"),
	password=os.environ.get("JENKINS_API_KEY")
	)
jobs = server.get_jobs()

releases = ['equuleus', 'sagitta', 'current']

for release_train in releases:
	os.makedirs(f'./_site/{release_train}/deb/pool/main/')
	for folder in jobs:
		if folder['name'] == f'vyos-{release_train}':
			for job in folder['jobs']:
				job_name = f'vyos-{release_train}/' + job['name']
				try:
					last_successful_build = server.get_job_info(job_name, 0, True)["lastSuccessfulBuild"]["number"]
					build_info = server.get_build_info(job_name, last_successful_build)
					artifacts = server.get_build_info(job_name, last_successful_build)["artifacts"]
					for artifact in artifacts:
						artifact_data = server.get_build_artifact_as_bytes(job_name, last_successful_build, artifact['relativePath'])
						with open(f'./_site/{release_train}/deb/pool/main/' + artifact["fileName"], 'wb') as artifact_file:
							artifact_file.write(artifact_data)
					# for artifact in artifacts:
					# 	artifact_data = requests.request(
					# 		method='GET',
					# 		url=f'{jenkins_url}/job/vyos-{release_train}/job/{job_name}/{last_successful_build}/artifact/{artifact["relativePath"]}',
					# 		auth=(os.environ.get("JENKINS_USERNAME"), os.environ.get("JENKINS_API_KEY")),
					# 		stream=True
					# 		)
					# 	with open(f'./_site/{release_train}/deb/pool/main/' + artifact["fileName"], 'wb') as artifact_file:
					# 		for chunk in artifact_data.raw(chunk_size=1024):
					# 			artifact_file.write(chunk)
				except TypeError:
					pass
