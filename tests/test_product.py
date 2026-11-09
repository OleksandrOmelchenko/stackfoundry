"""The product profile and the domain brief: `stackfoundry product check|status`."""
import json
import unittest
from datetime import date, timedelta

from tests._support import TempRepo, run_cli, write
from stackfoundry.product import check_domain, check_product, status

PRODUCT = {"schemaVersion": 1, "name": "Shop", "summary": "Sells books online.", "category": "B2C online store",
           "domainId": "b2c-ecommerce", "audiences": ["consumers"], "markets": ["ES"], "stage": "growth",
           "evidence": [{"claim": "has a cart", "where": "src/cart.py"}]}
SOURCES = {"gdpr": {"url": "https://gdpr.eu/", "accessed": "2026-11-09"},
           "baymard": {"url": "https://baymard.com/research", "accessed": "2026-11-09"}}


def brief(**over):
    data = {"schemaVersion": 1, "id": "b2c-ecommerce", "title": "B2C e-commerce", "researchedAt": "2026-11-09",
            "scope": {"category": "B2C online store", "audiences": ["consumers"], "markets": ["ES"]},
            "capabilities": [{"id": "order-tracking", "name": "Order tracking", "tier": "table-stakes",
                              "why": "Customers ask where their order is.", "signals": ["tracking", "shipment"],
                              "sources": ["baymard"]}],
            "regulations": [{"name": "GDPR", "appliesWhen": "EU customers", "obligations": ["data export"],
                             "sources": ["gdpr"]}],
            "weaknesses": [{"name": "Checkout friction", "failure": "abandoned carts", "lookFor": "forced sign-up",
                            "sources": ["baymard"]}],
            "sources": SOURCES}
    data.update(over)
    return data


class ProductCheckTests(unittest.TestCase):
    def test_a_valid_profile_passes(self):
        self.assertEqual(check_product(PRODUCT)[0], [])

    def test_each_profile_defect_is_reported(self):
        bad = {**PRODUCT, "stage": "beta", "domainId": "B2C Shop", "audiences": [], "color": "red",
               "evidence": [{"claim": "x"}], "summary": "Cart &amp; checkout"}
        errors = " | ".join(check_product(bad)[0])
        for needle in ("'stage' must be one of", "kebab-case", "'audiences' must be a non-empty", "unknown key 'color'",
                       "evidence[0] needs", "HTML-escaped"):
            self.assertIn(needle, errors)

    def test_a_valid_brief_passes(self):
        self.assertEqual(check_domain(brief())[0], [])

    def test_each_brief_defect_is_reported(self):
        caps = [{"id": "a", "name": "A", "tier": "must-have", "why": "w", "signals": ["s"], "sources": ["nowhere"]},
                {"id": "a", "name": "B", "tier": "expected", "why": "w", "signals": ["s"]}]
        errors = " | ".join(check_domain(brief(capabilities=caps, researchedAt="soon",
                                               trends=[{"name": "t", "what": "w", "maturity": "hot",
                                                        "sources": ["gdpr"]}]))[0])
        for needle in ("tier must be one of", "unknown source key(s): nowhere", "capabilities[1] cites no source",
                       "duplicate id 'a'", "researchedAt", "maturity must be one of"):
            self.assertIn(needle, errors)
        self.assertIn("no table-stakes capability", " ".join(check_domain(brief(capabilities=caps))[1]))

    def test_cli_tells_a_brief_from_a_profile(self):
        with TempRepo() as root:
            write(root, {".stackfoundry/product.json": json.dumps(PRODUCT),
                         ".stackfoundry/domain/b2c-ecommerce.json": json.dumps(brief())})
            for rel, kind in ((".stackfoundry/product.json", "product"),
                              (".stackfoundry/domain/b2c-ecommerce.json", "domain brief")):
                proc = run_cli(["product", "check", str(root / rel)])
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn(kind, proc.stdout)
            write(root, {".stackfoundry/product.json": json.dumps({**PRODUCT, "stage": "beta"})})
            self.assertEqual(run_cli(["product", "check", str(root / ".stackfoundry/product.json")]).returncode, 1)


class ProductStatusTests(unittest.TestCase):
    def test_missing_fresh_stale_and_moved(self):
        with TempRepo() as root:
            self.assertFalse(status(root)["productExists"])
            write(root, {".stackfoundry/product.json": json.dumps(PRODUCT)})
            self.assertEqual(status(root)["needsResearch"], "missing")
            today = date.today().isoformat()
            write(root, {".stackfoundry/domain/b2c-ecommerce.json": json.dumps(brief(researchedAt=today))})
            self.assertIsNone(status(root)["needsResearch"])
            old = (date.today() - timedelta(days=400)).isoformat()
            write(root, {".stackfoundry/domain/b2c-ecommerce.json": json.dumps(brief(researchedAt=old))})
            self.assertEqual(status(root)["needsResearch"], "stale")
            write(root, {".stackfoundry/domain/b2c-ecommerce.json": json.dumps(brief(researchedAt=today)),
                         ".stackfoundry/product.json": json.dumps({**PRODUCT, "markets": ["ES", "PT"]})})
            st = status(root)
            self.assertEqual((st["needsResearch"], st["scopeMoved"]), ("scope moved", ["markets"]))
            proc = run_cli(["product", "status", "--root", str(root)])
            self.assertEqual(json.loads(proc.stdout)["domainId"], "b2c-ecommerce")


if __name__ == "__main__":
    unittest.main()
