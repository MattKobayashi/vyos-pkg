#!/usr/bin/env python3

import os
import jenkins

jenkins_url = os.environ.get("JENKINS_SERVER")

server = jenkins.Jenkins(
    url=jenkins_url,
    username=os.environ.get("JENKINS_USERNAME"),
    password=os.environ.get("JENKINS_API_KEY")
)
root_jobs = server.get_jobs()

releases = ['equuleus', 'sagitta', 'current']

def download_artifacts(job_name, release_train, last_successful_build):
    artifacts = server.get_build_info(job_name, last_successful_build)["artifacts"]
    for artifact in artifacts:
        artifact_data = server.get_build_artifact_as_bytes(job_name, last_successful_build, artifact['relativePath'])
        artifact_path = f'./_site/{release_train}/deb/pool/main/{artifact["fileName"]}'
        with open(artifact_path, 'wb') as artifact_file:
            artifact_file.write(artifact_data)

for release_train in releases:
    os.makedirs(f'./_site/{release_train}/deb/pool/main/', exist_ok=True)
    for folder in root_jobs:
        if folder['name'] == f'vyos-{release_train}':
            for job in folder['jobs']:
                job_name = f'vyos-{release_train}/{job["name"]}'
                try:
                    last_successful_build = server.get_job_info(job_name, 0, True)["lastSuccessfulBuild"]["number"]
                    download_artifacts(job_name, release_train, last_successful_build)
                except TypeError:
                    pass
	