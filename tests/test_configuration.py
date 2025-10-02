from __future__ import annotations

from pathlib import Path
import json
import tempfile
import unittest

from engine.configuration import AdaptiveConfig, resolve_config_path


class ConfigurationTests(unittest.TestCase):
    def test_defaults_loaded_without_file(self) -> None:
        config = AdaptiveConfig(None).snapshot()
        self.assertEqual(config.composer.architecture, "hybrid")
        self.assertGreaterEqual(config.observer.min_delay, 1.0)

    def test_file_overrides_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"composer": {"architecture": "oracle", "max_layers": 4}}), encoding="utf-8")
            adaptive = AdaptiveConfig(path)
            snapshot = adaptive.snapshot()
            self.assertEqual(snapshot.composer.architecture, "oracle")
            self.assertEqual(snapshot.composer.max_layers, 4)

    def test_resolve_config_path_prefers_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "custom.json"
            candidate.write_text("{}", encoding="utf-8")
            self.addCleanup(lambda: __import__("os").environ.pop("INVITATION_CONFIG", None))
            __import__("os").environ["INVITATION_CONFIG"] = str(candidate)
            resolved = resolve_config_path(Path(tmp))
            self.assertEqual(resolved, candidate)


if __name__ == "__main__":
    unittest.main()
