#!/usr/bin/env python3

from datetime import datetime
import os
import re
import subprocess
import json_repair
import tomllib


def parse_jenkinsfile(content: str) -> list:
    """Parse Jenkinsfile content to extract package information.

    This function takes a Jenkinsfile content as input and extracts the package list
    along with relevant metadata. It processes the content by:
    1. Finding and extracting the pkgList definition
    2. Converting Jenkins syntax to valid JSON format
    3. Replacing placeholders with actual values (timestamp, commit_id, package_name)

    Args:
        content (str): Raw content of the Jenkinsfile to parse

    Returns:
        list: Processed and parsed package list data structure

    Raises:
        AttributeError: If required patterns are not found in the content
        json_repair.JSONDecodeError: If the resulting JSON structure is invalid

    Example:
        >>> content = '''def pkgList = [
        ...     'package-${timestamp}-${commit_id}'
        ... ]
        ... def commit_id = 'abc1234'
        ... '''
        >>> parse_jenkinsfile(content)
        ['package-20230615123456-abc1234']
    """
    pkglist_raw = re.search(r"def pkgList = \[\n.*?\n\]", content, re.DOTALL).group()
    pkglist_raw = (
        pkglist_raw.removeprefix("def pkgList = ")
        .replace("[", "{")
        .replace("]", "}")
        .replace("// ", "# ")
        .replace("'''", "'")
    )

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    commit_id = re.search(r"def commit_id = \'[0-9a-fA-F]{7}\'", content)
    package_name = re.search(r"def package_name = \'.*\'", content)

    replacements = {
        "${timestamp}": timestamp,
        "${commit_id}": commit_id.group().removeprefix("def commit_id = '").removesuffix("'") if commit_id else "",
        "${package_name}": (
            package_name.group().removeprefix("def package_name = '").removesuffix("'") if package_name else ""
        ),
    }

    for placeholder, value in replacements.items():
        pkglist_raw = pkglist_raw.replace(placeholder, value)

    return json_repair.loads(pkglist_raw)


def get_build_cmds(pkglist) -> list:
    """Processes build commands from a package list and returns a flattened list of commands.

    This function takes a package list (or single package) and processes the build commands,
    handling multi-line commands and filtering out comments. Each command is split on '&&'
    or ';' (except when followed by 'then').

    Args:
        pkglist (Union[list, dict]): A list of package dictionaries or a single package dictionary.
                                    Each package must contain a 'buildCmd' key.

    Returns:
        list: A flattened list of individual build commands, with comments removed and
              multi-line commands joined with '&&'.

    Example:
        >>> pkgs = [{'buildCmd': 'cmd1 && cmd2\ncmd3\n#comment\ncmd4'}]
        >>> get_build_cmds(pkgs)
        ['cmd1', 'cmd2', 'cmd3', 'cmd4']
    """
    if not isinstance(pkglist, list):
        pkglist = [pkglist]
    build_cmds = []

    for package in pkglist:
        if "\n" in package["buildCmd"]:
            package["buildCmd"] = " &&".join(filter(None, package["buildCmd"].split("\n")))

        commands = [cmd.strip() for cmd in re.split("&&|;(?! then)", package["buildCmd"])]
        build_cmds += [cmd for cmd in commands if not cmd.startswith("#")]

    return build_cmds


def main():
    """
    Main execution function that processes a Jenkinsfile to build packages.

    This function performs the following steps:
    1. Reads and parses a Jenkinsfile
    2. For each package defined in the Jenkinsfile:
        - Clones the source repository if SCM info is provided
        - Checks out specific commit if specified
        - Gets build commands for the package
        - For linux-kernel builds, substitutes kernel version from defaults.toml
        - Executes the build commands

    The function handles both single package and multiple package definitions in the Jenkinsfile.

    Returns:
         None

    Raises:
         FileNotFoundError: If Jenkinsfile or defaults.toml (for kernel builds) cannot be found
         subprocess.CalledProcessError: If a git or build command fails (suppressed by check=False)
    """
    with open("Jenkinsfile", encoding="utf-8") as jenkinsfile:
        content = jenkinsfile.read()

    pkglist = parse_jenkinsfile(content)

    if not isinstance(pkglist, list):
        pkglist = [pkglist]

    for package in pkglist:
        if "scmUrl" in package:
            subprocess.run(["git", "clone", package["scmUrl"], package["name"]], check=False)
            subprocess.run(["git", "checkout", package["scmCommit"]], cwd=package["name"], check=False)

        commands = get_build_cmds(package)

        if "linux-kernel" in os.getcwd():
            with open("../../data/defaults.toml", "rb") as f:
                kernel_version = tomllib.load(f)["kernel_version"]

            commands = [re.sub(r"\${KERNEL_VER}", kernel_version, cmd) for cmd in commands]
            commands = [cmd for cmd in commands if cmd not in ["if { $? -ne 0 }; then", "exit 1", "fi"]]

        subprocess.run("; ".join(commands), shell=True, cwd=package.get("name", "."), check=False)


if __name__ == "__main__":
    main()
