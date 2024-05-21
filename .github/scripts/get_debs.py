#!/usr/bin/env python3

import os
import urllib.request
import json

with urllib.request.urlopen("https://api.github.com/repos/MattKobayashi/vyos-pkg/releases") as response:
	response_json = response.read()
	response_dict = json.loads(response_json)

os.makedirs("_site/equuleus/deb/pool/main", exist_ok=True)
break_loop = False
for release in response_dict:
	if "equuleus" in release["tag_name"]:
		for asset in release["assets"]:
			urllib.request.urlretrieve(asset["browser_download_url"], "_site/equuleus/deb/pool/main/" + asset["name"])
		break_loop = True
	if break_loop == True:
		break

os.makedirs("_site/sagitta/deb/pool/main", exist_ok=True)
break_loop = False
for release in response_dict:
	if "sagitta" in release["tag_name"]:
		for asset in release["assets"]:
			urllib.request.urlretrieve(asset["browser_download_url"], "_site/sagitta/deb/pool/main/" + asset["name"])
		break_loop = True
	if break_loop == True:
		break

os.makedirs("_site/current/deb/pool/main", exist_ok=True)
break_loop = False
for release in response_dict:
	if "current" in release["tag_name"]:
		for asset in release["assets"]:
			urllib.request.urlretrieve(asset["browser_download_url"], "_site/current/deb/pool/main/" + asset["name"])
		break_loop = True
	if break_loop == True:
		break
