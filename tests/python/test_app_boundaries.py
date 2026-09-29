"""Guard app dependency boundaries that keep features independently maintainable."""

from pathlib import Path
import re
import unittest

LIB = Path(__file__).resolve().parents[2] / "app" / "flutter_app" / "lib"
IMPORTS = re.compile(r"^(?:import|export) 'package:simple_app/([^']+)'", re.MULTILINE)


class AppBoundaryTest(unittest.TestCase):
    def test_shared_code_does_not_depend_on_features_or_navigation(self):
        for area in ("core", "shared", "config"):
            for path in (LIB / area).rglob("*.dart"):
                for target in IMPORTS.findall(path.read_text(encoding="utf-8")):
                    with self.subTest(source=path.relative_to(LIB), target=target):
                        self.assertFalse(target.startswith(("feature/", "app/")))

    def test_only_dashboard_composes_other_features(self):
        for path in (LIB / "feature").rglob("*.dart"):
            feature = path.relative_to(LIB).parts[1]
            for target in IMPORTS.findall(path.read_text(encoding="utf-8")):
                with self.subTest(source=path.relative_to(LIB), target=target):
                    self.assertFalse(target.startswith("app/"))
                    if target.startswith("feature/") and feature != "dashboard":
                        self.assertEqual(target.split("/")[1], feature)
                    if feature == "dashboard":
                        self.assertFalse(target.startswith("feature/user_auth/"))

    def test_requests_and_ui_do_not_cross_responsibilities(self):
        for path in LIB.rglob("*.dart"):
            text = path.read_text(encoding="utf-8")
            with self.subTest(source=path.relative_to(LIB)):
                if path.name.endswith("_request.dart"):
                    self.assertNotIn("package:flutter/material.dart", text)
                if "ui" in path.relative_to(LIB).parts:
                    self.assertNotIn("dart:io", text)
                    self.assertNotIn("HttpClient(", text)
                if path != LIB / "config" / "routing.dart":
                    # Ignore prose comments; HTTP path literals belong to routing config.
                    code = re.sub(r"//[^\n]*", "", text)
                    self.assertIsNone(re.search(r"['\"]/((?:app|machine)/[^'\"]+)['\"]", code))


if __name__ == "__main__":
    unittest.main()
