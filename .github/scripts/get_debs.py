#!/usr/bin/env python3

from concurrent.futures import ThreadPoolExecutor
import logging
import os
from pathlib import Path
from typing import List, Dict, Any
import jenkins

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
RELEASES = ["equuleus", "sagitta", "current"]
POOL_DIR = "deb/pool/main"
MAX_WORKERS = 4


def setup_jenkins_connection() -> jenkins.Jenkins:
    """Initialize and return Jenkins server connection."""
    jenkins_url = os.environ.get("JENKINS_SERVER")
    if not jenkins_url:
        raise ValueError("JENKINS_SERVER environment variable not set")

    return jenkins.Jenkins(
        url=jenkins_url, username=os.environ.get("JENKINS_USERNAME"), password=os.environ.get("JENKINS_API_KEY")
    )


def create_directories(releases: List[str]) -> None:
    """Create necessary directories for artifacts."""
    for release in releases:
        Path(f"./_site/{release}/{POOL_DIR}").mkdir(parents=True, exist_ok=True)


def download_artifact(
    server: jenkins.Jenkins, job_name: str, build_number: int, artifact: Dict[str, Any], release: str
) -> None:
    """Download a single artifact from Jenkins."""
    try:
        artifact_data = server.get_build_artifact_as_bytes(job_name, build_number, artifact["relativePath"])
        output_path = Path(f'./_site/{release}/{POOL_DIR}/{artifact["fileName"]}')
        output_path.write_bytes(artifact_data)
        logging.info("Successfully downloaded %s", artifact["fileName"])
    except (jenkins.JenkinsException, OSError) as e:
        logging.error("Failed to download %s: %s", artifact["fileName"], str(e))


def process_job(server: jenkins.Jenkins, job_name: str, release: str) -> None:
    """Process a single Jenkins job."""
    try:
        job_info = server.get_job_info(job_name, 0, True)
        last_successful_build = job_info.get("lastSuccessfulBuild", {}).get("number")

        if not last_successful_build:
            logging.warning("No successful builds found for %s", job_name)
            return

        build_info = server.get_build_info(job_name, last_successful_build)
        artifacts = build_info["artifacts"]

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for artifact in artifacts:
                executor.submit(download_artifact, server, job_name, last_successful_build, artifact, release)
    except (jenkins.JenkinsException, KeyError) as e:
        logging.error("Error processing job %s: %s", job_name, str(e))


def main() -> None:
    """Main execution function."""
    try:
        server = setup_jenkins_connection()
        create_directories(RELEASES)
        root_jobs = server.get_jobs()

        for release in RELEASES:
            for folder in root_jobs:
                if folder["name"] == f"vyos-{release}":
                    for job in folder["jobs"]:
                        job_name = f'vyos-{release}/{job["name"]}'
                        process_job(server, job_name, release)

    except Exception as e:
        logging.error("Script execution failed: %s", str(e))
        raise


if __name__ == "__main__":
    main()
