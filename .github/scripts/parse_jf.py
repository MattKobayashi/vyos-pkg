#!/usr/bin/env python3

import re
from datetime import datetime
import json_repair
import subprocess

with open('Jenkinsfile') as myfile:
    content = myfile.read()

pkglist_raw = re.search(r'def pkgList = \[\n.*?\n\]', content, re.DOTALL) \
                .group() \
                .removeprefix('def pkgList = ')
pkglist_raw = pkglist_raw.replace("[", "{")
pkglist_raw = pkglist_raw.replace("]", "}")

if 'def timestamp = ' in content:
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    pkglist_raw = pkglist_raw.replace("${timestamp}", timestamp)

if 'def commit_id = ' in content:
    commit_id = re.search(r'def commit_id = \'[0-9a-fA-F]{7}\'', content, re.DOTALL) \
                    .group() \
                    .removeprefix('def commit_id = \'') \
                    .removesuffix('\'')
    pkglist_raw = pkglist_raw.replace("${commit_id}", commit_id)
    pkglist_raw = pkglist_raw.replace("commit_id", commit_id)

pkglist = json_repair.loads(pkglist_raw)

if isinstance(pkglist, list):
    for package in pkglist:
        subprocess.run(["git", "clone", package['scmUrl'], package['name']])
        subprocess.run(["git", "checkout", package['scmCommit']], cwd=package['name'])
        commands = re.split('&&|;', package['buildCmd'])
        for index, command in enumerate(commands):
            if "cd .." in command:
                continue
            if "cd .." in commands[index-1]:
                subprocess.run(command, shell=True)
                continue
            subprocess.run(command, shell=True, cwd=package['name'])
else:
    subprocess.run(["git", "clone", pkglist['scmUrl'], pkglist['name']])
    subprocess.run(["git", "checkout", pkglist['scmCommit']], cwd=pkglist['name'])
    commands = re.split('&&|;', pkglist['buildCmd'])
    for index, command in enumerate(commands):
        if "cd .." in command:
            continue
        if "cd .." in commands[index-1]:
            subprocess.run(command, shell=True)
            continue
        subprocess.run(command, shell=True, cwd=pkglist['name'])
