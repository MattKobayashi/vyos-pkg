#!/usr/bin/env python3

import re
from datetime import datetime
import json_repair
import subprocess
import os


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
    # Convert pkglist_raw to JSON
    pkglist = json_repair.loads(pkglist_raw)
    return pkglist


def getBuildCmds(pkglist) -> list:
    if isinstance(pkglist, list):
        for package in pkglist:
            # Handle Linux kernel build
            if '\n' in package['buildCmd']:
                cmdlist = package['buildCmd'].split('\n')
                cmdlist = list(filter(None, cmdlist))
                cmd = ' &&'.join(cmdlist)
                package['buildCmd'] = cmd
                kernel_ver = dict(
                    os.environ, \
                    KERNEL_VER=subprocess.run(['cat ../../data/defaults.toml | tomlq -r .kernel_version'], shell=True, capture_output=True) \
                    .stdout.decode('utf-8') \
                    .rstrip()
                    )
            # Split build commands
            commands = re.split('&&|;(?! then)', package['buildCmd'])
            # Remove instances of 'cd ..'
            commands = [command for command in commands if 'cd ..' not in command]
            # Strip whitespace
            commands = [command.strip() for command in commands]
            return commands
    else:
        # Handle Linux kernel build
        if '\n' in pkglist['buildCmd']:
            cmdlist = pkglist['buildCmd'].split('\n')
            cmdlist = list(filter(None, cmdlist))
            cmd = ' &&'.join(cmdlist)
            pkglist['buildCmd'] = cmd
            kernel_ver = dict(
                os.environ, \
                KERNEL_VER=subprocess.run(['cat ../../data/defaults.toml | tomlq -r .kernel_version'], shell=True, capture_output=True) \
                .stdout.decode('utf-8') \
                .rstrip()
                )
        # Split build commands
        commands = re.split('&&|;(?! then)', pkglist['buildCmd'])
        # Remove instances of 'cd ..'
        commands = [command for command in commands if 'cd ..' not in command]
        # Strip whitespace
        commands = [command.strip() for command in commands]
        return commands


# Read Jenkinsfile
with open('Jenkinsfile') as jenkinsfile:
    content = jenkinsfile.read()

# Parse Jenkinsfile
pkglist = parseJenkinsfile(content)

# Main package loop
if isinstance(pkglist, list):
    for package in pkglist:
        # Do `git clone` and `git checkout` things
        if 'scmUrl' in package:
            subprocess.run(['git', 'clone', package['scmUrl'], package['name']])
            subprocess.run(['git', 'checkout', package['scmCommit']], cwd=package['name'])
        # Get build commands
        commands = getBuildCmds(package)
        # Run each build command
        for command in commands:
            if 'kernel' in package['name']:
                subprocess.run(command, shell=True, env=kernel_ver)
                continue
            else:
                subprocess.run(command, shell=True, cwd=package['name'])
else:
    # Do `git clone` and `git checkout` things
    if 'scmUrl' in pkglist:
        subprocess.run(['git', 'clone', pkglist['scmUrl'], pkglist['name']])
        subprocess.run(['git', 'checkout', pkglist['scmCommit']], cwd=pkglist['name'])
    # Get build commands
    commands = getBuildCmds(pkglist)
    # Run each build command
    for command in commands:
        if 'kernel' in pkglist['name']:
            subprocess.run(command, shell=True, env=kernel_ver)
            continue
        else:
            subprocess.run(command, shell=True, cwd=pkglist['name'])
