import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "check-fit.py"
spec = importlib.util.spec_from_file_location("check_fit", SCRIPT)
check_fit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_fit)

LIMIT_RANGE = {
    "min": {"cpu": "50m", "memory": "64Mi"},
    "max": {"cpu": "1", "memory": "1Gi"},
    "maxLimitRequestRatio": {"cpu": "4", "memory": "4"},
}


def container(requests, limits):
    return {"name": "c", "resources": {"requests": requests, "limits": limits}}


class ParseQuantityTest(unittest.TestCase):
    def test_units(self):
        self.assertEqual(check_fit.parse_quantity("250m"), 0.25)
        self.assertEqual(check_fit.parse_quantity("1Gi"), 2**30)
        self.assertEqual(check_fit.parse_quantity("2"), 2.0)


class CheckContainerTest(unittest.TestCase):
    def test_fitting_container_passes(self):
        c = container({"cpu": "100m", "memory": "128Mi"}, {"cpu": "200m", "memory": "256Mi"})
        self.assertEqual(check_fit.check_container("d", c, LIMIT_RANGE), [])

    def test_missing_limits_are_reported(self):
        errors = check_fit.check_container("d", {"name": "c"}, LIMIT_RANGE)
        self.assertEqual(len(errors), 2)

    def test_limit_above_max_is_reported(self):
        c = container({"cpu": "500m", "memory": "128Mi"}, {"cpu": "2", "memory": "256Mi"})
        errors = check_fit.check_container("d", c, LIMIT_RANGE)
        self.assertTrue(any("exceeds LimitRange max" in e for e in errors))

    def test_ratio_above_bound_is_reported(self):
        c = container({"cpu": "100m", "memory": "64Mi"}, {"cpu": "500m", "memory": "128Mi"})
        errors = check_fit.check_container("d", c, LIMIT_RANGE)
        self.assertTrue(any("ratio" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
