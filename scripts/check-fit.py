#!/usr/bin/env python3
"""Fail when a workload would be rejected by the namespace's LimitRange or quota.

The API server only enforces these at admission time, so a Deployment that is
too big applies cleanly and then never creates its pods. Checking up front
turns that silent failure into a CI error.
"""
import pathlib
import sys

import yaml

MANIFEST_DIR = pathlib.Path(__file__).resolve().parent.parent / "manifests"

SUFFIXES = {
    "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40,
    "k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12,
    "m": 1e-3,
}
RESOURCES = ("cpu", "memory")


def parse_quantity(value):
    text = str(value)
    for suffix, factor in SUFFIXES.items():
        if text.endswith(suffix):
            return float(text[: -len(suffix)]) * factor
    return float(text)


def load_docs():
    for path in sorted(MANIFEST_DIR.glob("*.yaml")):
        for doc in yaml.safe_load_all(path.read_text()):
            if doc:
                yield doc


def check_container(workload, container, limit_range):
    errors = []
    name = f"{workload}/{container['name']}"
    resources = container.get("resources", {})
    requests = resources.get("requests", {})
    limits = resources.get("limits", {})
    for res in RESOURCES:
        if res not in requests or res not in limits:
            errors.append(f"{name}: {res} needs both a request and a limit")
            continue
        req, lim = parse_quantity(requests[res]), parse_quantity(limits[res])
        if lim < req:
            errors.append(f"{name}: {res} limit {limits[res]} is below request {requests[res]}")
        low = limit_range.get("min", {}).get(res)
        high = limit_range.get("max", {}).get(res)
        if low and req < parse_quantity(low):
            errors.append(f"{name}: {res} request {requests[res]} is below LimitRange min {low}")
        if high and lim > parse_quantity(high):
            errors.append(f"{name}: {res} limit {limits[res]} exceeds LimitRange max {high}")
        ratio = limit_range.get("maxLimitRequestRatio", {}).get(res)
        if ratio and req and lim / req > parse_quantity(ratio):
            errors.append(f"{name}: {res} limit/request ratio exceeds {ratio}")
    return errors


def main():
    docs = list(load_docs())
    limit_range = next(
        (limit for d in docs if d["kind"] == "LimitRange" for limit in d["spec"]["limits"] if limit["type"] == "Container"),
        {},
    )
    errors = []
    totals = {f"{kind}.{res}": 0.0 for kind in ("requests", "limits") for res in RESOURCES}
    pods = 0
    for doc in docs:
        if doc["kind"] != "Deployment":
            continue
        replicas = doc["spec"].get("replicas", 1)
        pods += replicas
        for container in doc["spec"]["template"]["spec"]["containers"]:
            errors += check_container(doc["metadata"]["name"], container, limit_range)
            for kind in ("requests", "limits"):
                for res, value in container.get("resources", {}).get(kind, {}).items():
                    if f"{kind}.{res}" in totals:
                        totals[f"{kind}.{res}"] += parse_quantity(value) * replicas
    hard = {}
    for doc in docs:
        if doc["kind"] == "ResourceQuota":
            hard.update(doc["spec"]["hard"])
    for key, used in totals.items():
        if key in hard and used > parse_quantity(hard[key]):
            errors.append(f"quota: {key} needs {used:g} but the namespace allows {hard[key]}")
    if "pods" in hard and pods > int(hard["pods"]):
        errors.append(f"quota: {pods} pods requested but the namespace allows {hard['pods']}")
    for err in errors:
        print(err, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
