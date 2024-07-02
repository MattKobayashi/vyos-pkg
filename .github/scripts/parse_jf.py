#!/usr/bin/env python3

import re
from datetime import datetime
import json_repair
import subprocess
import os
import tomllib


def parseJenkinsfile(content: str) -> list:
    # Initialise the pkglist_raw string
    pkglist_raw = re.search(r'def pkgList = \[\n.*?\n\]', content, re.DOTALL) \
                .group() \
                .removeprefix('def pkgList = ')
    # Other replacements
    pkglist_raw = pkglist_raw.replace('[', '{')
    pkglist_raw = pkglist_raw.replace(']', '}')
    pkglist_raw = pkglist_raw.replace('// ', '# ')
    pkglist_raw = pkglist_raw.replace("'''", "'")
    # Replace timestamp placeholder if it exists
    if 'def timestamp = ' in content:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pkglist_raw = pkglist_raw.replace('${timestamp}', timestamp)
    # Replace commit_id placeholder if it exists
    if 'def commit_id = ' in content:
        commit_id = re.search(r'def commit_id = \'[0-9a-fA-F]{7}\'', content, re.DOTALL) \
                        .group() \
                        .removeprefix('def commit_id = \'') \
                        .removesuffix('\'')
        pkglist_raw = pkglist_raw.replace('${commit_id}', commit_id)
        pkglist_raw = pkglist_raw.replace('commit_id', commit_id)
    # Replace package_name placeholder if it exists
    if 'def package_name = ' in content:
        package_name = re.search(r'def package_name = \'.*\'', content, re.DOTALL) \
                        .group() \
                        .removeprefix('def package_name = \'') \
                        .removesuffix('\'')
        pkglist_raw = pkglist_raw.replace('${package_name}', package_name)
        pkglist_raw = pkglist_raw.replace('package_name', package_name)
    # Convert pkglist_raw to JSON
    pkglist = json_repair.loads(pkglist_raw)
    return pkglist


def getBuildCmds(pkglist) -> list:
    if not isinstance(pkglist, list):
        pkglist = [pkglist]
    for package in pkglist:
        # Handle Linux kernel build
        if '\n' in package['buildCmd']:
            cmdlist = package['buildCmd'].split('\n')
            cmdlist = list(filter(None, cmdlist))
            cmd = ' &&'.join(cmdlist)
            package['buildCmd'] = cmd
        # Split build commands
        commands = re.split('&&|;(?! then)', package['buildCmd'])
        # Strip whitespace
        commands = [command.strip() for command in commands]
        # Remove comments
        commands = [command for command in commands if not command.startswith('#')]
        return commands


# Read Jenkinsfile
with open('Jenkinsfile') as jenkinsfile:
    content = jenkinsfile.read()

# Parse Jenkinsfile
pkglist = parseJenkinsfile(content)

# If it ain't a list, make it one
if not isinstance(pkglist, list):
    pkglist = [pkglist]

# Main package loop
for package in pkglist:
    # Do `git clone` and `git checkout` things
    if 'scmUrl' in package:
        subprocess.run(['git', 'clone', package['scmUrl'], package['name']])
        subprocess.run(['git', 'checkout', package['scmCommit']], cwd=package['name'])
    # Get build commands
    commands = getBuildCmds(package)
    # Run each build command
    if 'linux-kernel' in os.getcwd():
        # Extract kernel version from defaults.toml
        with open('../../data/defaults.toml', 'rb') as f:
            defaults_toml = tomllib.load(f)
        kernel_version = defaults_toml['kernel_version']
        # Remove flow control
        for index, command in enumerate(commands):
            commands[index] = re.sub(r'\${KERNEL_VER}', kernel_version, command)
            if command in ['if { $? -ne 0 }; then', 'exit 1', 'fi']:
                commands.pop(index)
        subprocess.run('; '.join(commands), shell=True)
    else:
        subprocess.run('; '.join(commands), shell=True, cwd=package['name'])
