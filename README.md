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
