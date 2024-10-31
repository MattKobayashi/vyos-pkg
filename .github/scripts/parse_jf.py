#!/usr/bin/env python3

import re
from datetime import datetime
import json_repair
import subprocess
import os
import tomllib


def parse_jenkinsfile(content: str) -> list:
    pkglist_raw = re.search(r'def pkgList = \[\n.*?\n\]', content, re.DOTALL).group()
    pkglist_raw = (pkglist_raw
                   .removeprefix('def pkgList = ')
                   .replace('[', '{')
                   .replace(']', '}')
                   .replace('// ', '# ')
                   .replace("'''", "'"))

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    commit_id = re.search(r'def commit_id = \'[0-9a-fA-F]{7}\'', content)
    package_name = re.search(r'def package_name = \'.*\'', content)

    replacements = {
        '${timestamp}': timestamp,
        '${commit_id}': commit_id.group().removeprefix('def commit_id = \'').removesuffix('\'') if commit_id else '',
        '${package_name}': package_name.group().removeprefix('def package_name = \'').removesuffix('\'') if package_name else '',
    }

    for placeholder, value in replacements.items():
        pkglist_raw = pkglist_raw.replace(placeholder, value)

    return json_repair.loads(pkglist_raw)


def get_build_cmds(pkglist) -> list:
    if not isinstance(pkglist, list):
        pkglist = [pkglist]
    build_cmds = []

    for package in pkglist:
        if '\n' in package['buildCmd']:
            package['buildCmd'] = ' &&'.join(filter(None, package['buildCmd'].split('\n')))
        
        commands = [cmd.strip() for cmd in re.split('&&|;(?! then)', package['buildCmd'])]
        build_cmds += [cmd for cmd in commands if not cmd.startswith('#')]
        
    return build_cmds


def main():
    with open('Jenkinsfile') as jenkinsfile:
        content = jenkinsfile.read()

    pkglist = parse_jenkinsfile(content)

    if not isinstance(pkglist, list):
        pkglist = [pkglist]

    for package in pkglist:
        if 'scmUrl' in package:
            subprocess.run(['git', 'clone', package['scmUrl'], package['name']])
            subprocess.run(['git', 'checkout', package['scmCommit']], cwd=package['name'])

        commands = get_build_cmds(package)

        if 'linux-kernel' in os.getcwd():
            with open('../../data/defaults.toml', 'rb') as f:
                kernel_version = tomllib.load(f)['kernel_version']

            commands = [re.sub(r'\${KERNEL_VER}', kernel_version, cmd) for cmd in commands]
            commands = [cmd for cmd in commands if cmd not in ['if { $? -ne 0 }; then', 'exit 1', 'fi']]

        subprocess.run('; '.join(commands), shell=True, cwd=package.get('name', '.'))


if __name__ == "__main__":
    main()
