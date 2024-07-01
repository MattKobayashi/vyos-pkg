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
            # Strip whitespace
            commands = [command.strip() for command in commands]
            # Remove comments
            commands = [command for command in commands if not command.startswith('#')]
            return commands
    else:
        # Handle Linux kernel build
        if '\n' in pkglist['buildCmd']:
            cmdlist = pkglist['buildCmd'].split('\n')
            cmdlist = list(filter(None, cmdlist))
            cmd = ' &&'.join(cmdlist)
            pkglist['buildCmd'] = cmd
        # Split build commands
        commands = re.split('&&|;(?! then)', pkglist['buildCmd'])
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
        kernel_ver = dict(
            os.environ, \
            KERNEL_VER=subprocess.run(
                ['cat ../../data/defaults.toml | tomlq -r .kernel_version'],
                shell=True, capture_output=True
                ) \
            .stdout.decode('utf-8') \
            .rstrip()
            )
        # Remove flow control
        for index, command in enumerate(commands):
            if command in ['if { $? -ne 0 }; then', 'exit 1', 'fi']:
                commands.pop(index)
        # commands = '''
        # gpg2 --locate-keys torvalds@kernel.org gregkh@kernel.org
        # curl -OL https://www.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VER}.tar.xz
        # curl -OL https://www.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VER}.tar.sign
        # xz -cd linux-${KERNEL_VER}.tar.xz | gpg2 --verify linux-${KERNEL_VER}.tar.sign -
        # if [ $? -ne 0 ]; then
        #     exit 1
        # fi
        # tar xf linux-${KERNEL_VER}.tar.xz
        # ln -s linux-${KERNEL_VER} linux
        # ./build-kernel.sh
        # '''
        subprocess.run('; '.join(commands), shell=True, env=kernel_ver)
    else:
        subprocess.run('; '.join(commands), shell=True, cwd=package['name'])
