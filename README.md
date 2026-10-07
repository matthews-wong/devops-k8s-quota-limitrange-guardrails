# k8s-quota-limitrange-guardrails

Namespace guardrails for a shared cluster: a `ResourceQuota` caps what a team
can consume, a `LimitRange` gives every container sane defaults (and rejects
absurd ones), and a small script checks that the workloads in this repo
actually fit inside those limits before anything reaches a cluster.

## Layout

- `manifests/` — namespace, quota, limit range and a sample workload
- `scripts/check-fit.py` — verifies each container fits the LimitRange and the
  namespace quota
- `Makefile` — `make validate` runs kubeconform and the fit check

## Validate

```sh
make validate
```

Needs `kubeconform` and Python 3 with PyYAML.

## Design notes

- The LimitRange default (`100m`/`128Mi` request, `500m`/`256Mi` limit) means a
  container that forgets `resources` still gets bounded. The sample Deployment
  sets its own anyway, so it does not depend on admission defaults.
- `maxLimitRequestRatio` is 4, so a pod cannot request almost nothing and burst
  to the container max.
- The quota is checked against `replicas × per-container resources`. Rolling
  updates briefly add surge pods, so leave headroom beyond what the check
  requires.
- The `nginx-unprivileged` image is a stand-in; swap in a real image and keep
  the pinned tag.
