"""Resolve upstream HEAD once and validate its recorded build provenance."""
import re
import subprocess

SHA = re.compile(r"[0-9a-f]{40}")


def branch_ref(value):
    return isinstance(value, str) and value.startswith("refs/heads/") and len(value) > 11 and not any(c.isspace() for c in value)


def resolve(source):
    baseline = source["commit"]
    if not SHA.fullmatch(baseline):
        raise ValueError("Invalid baseline ReSukiSU commit")
    output = subprocess.check_output(
        ["git", "ls-remote", "--symref",
         "https://github.com/" + source["repository"] + ".git", "HEAD"],
        text=True, timeout=60)
    commits, refs = [], []
    for line in output.splitlines():
        value, separator, name = line.partition("\t")
        if separator and name == "HEAD":
            if value.startswith("ref: "):
                refs.append(value[5:])
            elif SHA.fullmatch(value):
                commits.append(value)
    if len(commits) != 1 or len(refs) != 1 or not branch_ref(refs[0]):
        raise ValueError("Could not resolve ReSukiSU default branch and commit")
    selected = dict(source, commit=commits[0])
    selection = {"mode": "latest", "baseline_commit": baseline,
                 "requested_ref": "HEAD", "resolved_ref": refs[0]}
    return selected, selection


def validate_manifest(manifest, source):
    actual = manifest.get("resukisu")
    selection = manifest.get("resukisu_selection")
    if selection is None:
        if actual != source:
            raise ValueError("Stale or unrecorded ReSukiSU source")
        return  # Preserve compatibility with existing release manifests.
    if not isinstance(actual, dict) or not isinstance(selection, dict):
        raise ValueError("Invalid ReSukiSU provenance")
    commit = actual.get("commit")
    if not isinstance(commit, str) or not SHA.fullmatch(commit):
        raise ValueError("Invalid resolved ReSukiSU commit")
    if actual != dict(source, commit=commit) or selection.get("baseline_commit") != source["commit"]:
        raise ValueError("ReSukiSU repository, hook or baseline changed")
    if selection.get("mode") != "latest" or selection.get("requested_ref") != "HEAD" or not branch_ref(selection.get("resolved_ref")):
        raise ValueError("Invalid latest ReSukiSU branch provenance")
