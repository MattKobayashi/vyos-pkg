#!/usr/bin/env python3

import os
import jenkins
from pathlib import Path
import logging

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
    try:
        artifacts = server.get_build_info(jenkins_job_name, build_number)["artifacts"]
        for artifact in artifacts:
            artifact_data = server.get_build_artifact_as_bytes(jenkins_job_name, build_number, artifact["relativePath"])
            artifact_path = Path(f'./_site/{release_branch}/deb/pool/main/') / artifact["fileName"]
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            with open(artifact_path, "wb") as artifact_file:
                artifact_file.write(artifact_data)
    except Exception as e:
        logging.error(f"Failed to download artifact {artifact['fileName']}: {e}")
        raise e


for release_train in releases:
    for folder in root_jobs:
        if folder["name"] == f"vyos-{release_train}":
            for job in folder["jobs"]:
                full_job_path = f'vyos-{release_train}/{job["name"]}'
                try:
                    last_successful_build = server.get_job_info(full_job_path, 0, True)["lastSuccessfulBuild"]["number"]
                    download_artifacts(full_job_path, release_train, last_successful_build)
                except TypeError:
                    pass
                except Exception as e:
                    print(f"Error downloading artifacts for {full_job_path}: {e}")
                    continue
