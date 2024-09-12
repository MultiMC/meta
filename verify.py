#!/usr/bin/python3

import datetime
import hashlib
import json
from pathlib import Path

import requests

from metautil import *

print("collecting artifacts")
artifacts = set()

for json_file in sorted(Path(f"multimc").glob("**/*.json")):
    if json_file.name in ("index.json", "package.json"):
        continue

    version_file = MultiMCVersionFile(json.loads(json_file.read_text()))
    libraries = list()
    for key, value in version_file.items():
        if isinstance(value, MultiMCLibrary):
            libraries.append(value)
        elif isinstance(value, list):
            for entry in value:
                if isinstance(entry, MultiMCLibrary):
                    libraries.append(entry)

    for library in libraries:
        if not library.downloads:
            url = library.url or "https://libraries.minecraft.net/"
            if not url.endswith("/"):
                url += "/"
            url += library.name.getPath()
            artifact = MojangArtifactBase({"url": url})
            artifacts.add(json.dumps(artifact.to_json()))
        else:
            classifiers = library.downloads.classifiers or {}
            for artifact in [library.downloads.artifact, *classifiers.values()]:
                if artifact:
                    artifacts.add(json.dumps(artifact.to_json()))

artifacts = [MojangArtifact(json.loads(artifact)) for artifact in artifacts]
artifacts.sort(key=lambda artifact: artifact.url)

print(f"checking {len(artifacts)} artifacts")
problems = list()
problems_json = Path("problems.json")

session = requests.session()
i_max = len(artifacts)
start = datetime.datetime.now().replace(microsecond=0)
for i, artifact in enumerate(artifacts, start=1):
    i = str(i).rjust(len(str(i_max)), "0")
    runtime = datetime.datetime.now().replace(microsecond=0) - start
    print(f"{runtime} {i}/{i_max} {artifact.url}")

    if artifact.sha1 or artifact.size:
        r = session.get(artifact.url, allow_redirects=True)
    else:
        r = session.head(artifact.url, allow_redirects=True)

    artifact_problems = dict()
    
    if not r.ok:
        artifact_problems["status"] = r.status_code

    else:
        if artifact.sha1:
            sha1 = hashlib.sha1(r.content).hexdigest()
            if artifact.sha1 != sha1:
                artifact_problems["sha1"] = sha1

        if artifact.size:
            size = len(r.content)
            if artifact.size != size:
                artifact_problems["size"] = size
    
    if artifact_problems:
        artifact_problems = {
            "artifact": artifact.to_json(),
            "problems": artifact_problems,
        }
        print(json.dumps(artifact_problems, indent=2))
        problems.append(artifact_problems)
        problems_json.write_text(json.dumps(problems, indent=2))

if problems:
    print(f"found {len(problems)} problems, check {problems_json}")
else:
    print("no problems found 🥳")
    if problems_json.exists():
        problems_json.unlink()
