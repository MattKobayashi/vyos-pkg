#!/usr/bin/env python3

import os
import jenkins

jenkins_url = os.environ.get("JENKINS_SERVER")

server = jenkins.Jenkins(
    url=jenkins_url, username=os.environ.get("JENKINS_USERNAME"), password=os.environ.get("JENKINS_API_KEY")
)
root_jobs = server.get_jobs()

releases = ["equuleus", "sagitta", "current"]


def download_artifacts(jenkins_job_name, release_branch, build_number):
    """Downloads artifacts from a Jenkins build and saves them locally.

    Args:
        jenkins_job_name (str): Name of the Jenkins job to download artifacts from
        release_branch (str): Release train name used in the path structure (e.g. 'current', 'equuleus')
        build_number (int): Build number of the last successful Jenkins build
    """
    artifacts = server.get_build_info(jenkins_job_name, build_number)["artifacts"]
    for artifact in artifacts:
        artifact_data = server.get_build_artifact_as_bytes(jenkins_job_name, build_number, artifact["relativePath"])
        artifact_path = f'./_site/{release_branch}/deb/pool/main/{artifact["fileName"]}'
        with open(artifact_path, "wb") as artifact_file:
            artifact_file.write(artifact_data)


for release_train in releases:
    os.makedirs(f"./_site/{release_train}/deb/pool/main/", exist_ok=True)
    for folder in root_jobs:
        if folder["name"] == f"vyos-{release_train}":
            for job in folder["jobs"]:
                full_job_path = f'vyos-{release_train}/{job["name"]}'
                try:
                    last_successful_build = server.get_job_info(full_job_path, 0, True)["lastSuccessfulBuild"]["number"]
                    download_artifacts(full_job_path, release_train, last_successful_build)
                except TypeError:
                    pass
