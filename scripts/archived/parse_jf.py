#!/usr/bin/env python3

from datetime import datetime
import logging
import os
from pathlib import Path
import re
import subprocess
import tomllib
from typing import List, Dict, Union, Optional
import json_repair

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
KERNEL_VERSION_FILE = Path("../../data/defaults.toml")
TIMESTAMP_FORMAT = "%Y%m%d%H%M%S"


def parse_jenkinsfile(content: str) -> List[Dict[str, str]]:
    """Parse Jenkinsfile content and extract package information.

    Args:
        content: Raw Jenkinsfile content
    Returns:
        List of package configurations
    Raises:
        ValueError: If required package list section is not found
    """
    try:
        pkglist_raw = re.search(r"def pkgList = \[\n.*?\n\]", content, re.DOTALL)
        if not pkglist_raw:
            raise ValueError("Could not find package list in Jenkinsfile")

        pkglist_raw = pkglist_raw.group().removeprefix("def pkgList = ")

        # Process replacements
        replacements = {"[": "{", "]": "}", "// ": "# ", "'''": "'"}
        for old, new in replacements.items():
            pkglist_raw = pkglist_raw.replace(old, new)

        # Handle dynamic variables
        variables = {
            "timestamp": lambda: datetime.now().strftime(TIMESTAMP_FORMAT),
            "commit_id": lambda: _extract_value(content, r"def commit_id = \'([0-9a-fA-F]{7})\'"),
            "package_name": lambda: _extract_value(content, r"def package_name = \'(.*)\'"),
        }

        for var_name, extractor in variables.items():
            if f"def {var_name} = " in content:
                value = extractor()
                pkglist_raw = pkglist_raw.replace(f"${{{var_name}}}", value)
                pkglist_raw = pkglist_raw.replace(var_name, value)

        return json_repair.loads(pkglist_raw)
    except Exception as e:
        logger.error("Failed to parse Jenkinsfile: %s", str(e))
        raise


def _extract_value(content: str, pattern: str) -> str:
    """Extract value from content using regex pattern."""
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        raise ValueError(f"Could not extract value using pattern: {pattern}")
    return match.group(1)


def get_build_cmds(package: Union[Dict[str, str], List[Dict[str, str]]]) -> List[str]:
    """Extract and process build commands from package configuration.

    Args:
        package: Package configuration dict or list
    Returns:
        List of processed build commands
    """
    if not isinstance(package, list):
        package = [package]

    commands = []
    for pkg in package:
        if "\n" in pkg["buildCmd"]:
            commands.extend(filter(None, pkg["buildCmd"].split("\n")))
        else:
            commands.extend(re.split("&&|;(?! then)", pkg["buildCmd"]))

    # Clean up commands
    return [cmd.strip() for cmd in commands if cmd.strip() and not cmd.strip().startswith("#")]


def run_command(cmd: str, cwd: Optional[str] = None) -> None:
    """Execute shell command safely."""
    try:
        logger.info("Running command: %s", cmd)
        result = subprocess.run(cmd, shell=True, cwd=cwd, check=True, text=True, capture_output=True)
        logger.info("Command output: %s", result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("Command failed: %s", str(e))
        logger.error("Error output: %s", e.stderr)
        raise


def main():
    """Main execution function for the Jenkinsfile parser and build script.

    This function handles the process of reading a Jenkinsfile, parsing package information,
    and executing build commands for each package. It performs the following steps:
    1. Reads and parses the Jenkinsfile
    2. For each package:
        - Handles SCM operations (git clone/checkout) if scm info is present
        - Generates build commands
        - Executes commands with special handling for linux-kernel builds

    Raises:
         Exception: Any error during execution is logged and re-raised

    Note:
         For linux-kernel builds, the function reads kernel version from a TOML file
         and substitutes ${KERNEL_VER} in the build commands.
    """
    try:
        # Read Jenkinsfile
        with open("Jenkinsfile", encoding="utf-8") as jenkinsfile:
            content = jenkinsfile.read()

        pkglist = parse_jenkinsfile(content)
        if not isinstance(pkglist, list):
            pkglist = [pkglist]

        for package in pkglist:
            # Handle SCM operations
            if "scmUrl" in package:
                run_command(f"git clone {package['scmUrl']} {package['name']}")
                run_command(f"git checkout {package['scmCommit']}", cwd=package["name"])

            commands = get_build_cmds(package)

            if "linux-kernel" in os.getcwd():
                # Handle kernel build
                with open(KERNEL_VERSION_FILE, "rb") as f:
                    kernel_version = tomllib.load(f)["kernel_version"]

                commands = [cmd for cmd in commands if cmd not in ["if { $? -ne 0 }; then", "exit 1", "fi"]]
                commands = [re.sub(r"\${KERNEL_VER}", kernel_version, cmd) for cmd in commands]

                run_command("; ".join(commands))
            else:
                run_command("; ".join(commands), cwd=package["name"])

    except Exception as e:
        logger.error("Script failed: %s", str(e))
        raise


if __name__ == "__main__":
    main()
