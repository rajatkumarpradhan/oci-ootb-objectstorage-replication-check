import unittest

from repl_checker.model import Bucket, ReplicationPolicy
from repl_checker.rules import (
    exit_code,
    rule_bad_destination,
    rule_chained_replication,
    rule_policy_not_active,
    rule_prod_without_policy,
    run_all,
)


def bucket(name="b", region="r1", versioning="Disabled", retention=False,
           criticality="dev", repl=None):
    return Bucket(
        name=name,
        region=region,
        versioning=versioning,
        has_retention_rules=retention,
        tags={"criticality": criticality},
        replication=repl,
    )


def pol(dest="dest", region="r2", status="ACTIVE"):
    return ReplicationPolicy(name="p", destination_bucket=dest,
                             destination_region=region, status=status)


class TestRepl001(unittest.TestCase):
    def test_fires_prod_no_policy(self):
        out = rule_prod_without_policy((bucket(criticality="prod"),))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "HIGH")

    def test_quiet_dev_no_policy(self):
        self.assertEqual(rule_prod_without_policy((bucket(),)), [])

    def test_quiet_prod_with_policy(self):
        self.assertEqual(rule_prod_without_policy((bucket(criticality="prod", repl=pol()),)), [])


class TestRepl002(unittest.TestCase):
    def test_fires_versioned_destination(self):
        bs = (bucket(name="src", repl=pol(dest="dst")),
              bucket(name="dst", versioning="Enabled"))
        out = rule_bad_destination(bs)
        self.assertEqual(len(out), 1)
        self.assertIn("versioning", out[0].detail)

    def test_fires_retention_destination(self):
        bs = (bucket(name="src", repl=pol(dest="dst")),
              bucket(name="dst", retention=True))
        self.assertEqual(len(rule_bad_destination(bs)), 1)

    def test_quiet_clean_destination(self):
        bs = (bucket(name="src", repl=pol(dest="dst")), bucket(name="dst"))
        self.assertEqual(rule_bad_destination(bs), [])

    def test_destination_outside_export_skipped(self):
        self.assertEqual(rule_bad_destination((bucket(name="src", repl=pol(dest="elsewhere")),)), [])


class TestRepl003(unittest.TestCase):
    def test_fires_on_chain(self):
        bs = (bucket(name="a", repl=pol(dest="b")),
              bucket(name="b", repl=pol(dest="c")))
        out = rule_chained_replication(bs)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "MEDIUM")

    def test_quiet_without_chain(self):
        bs = (bucket(name="a", repl=pol(dest="b")), bucket(name="b"))
        self.assertEqual(rule_chained_replication(bs), [])


class TestRepl004(unittest.TestCase):
    def test_fires_on_error_status(self):
        out = rule_policy_not_active((bucket(name="a", repl=pol(status="ERROR")),))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0].severity, "LOW")

    def test_quiet_when_active(self):
        self.assertEqual(rule_policy_not_active((bucket(name="a", repl=pol(status="ACTIVE")),)), [])


class TestAggregation(unittest.TestCase):
    def test_exit_2_on_high(self):
        self.assertEqual(exit_code(run_all((bucket(criticality="prod"),))), 2)

    def test_exit_1_medium_only(self):
        bs = (bucket(name="src", repl=pol(dest="dst")), bucket(name="dst", retention=True))
        self.assertEqual(exit_code(run_all(bs)), 1)

    def test_exit_0_clean(self):
        bs = (bucket(name="src", criticality="prod", repl=pol(dest="dst")), bucket(name="dst"))
        self.assertEqual(exit_code(run_all(bs)), 0)


if __name__ == "__main__":
    unittest.main()
