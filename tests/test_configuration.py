import json
import os
from pathlib import Path
import tempfile
import unittest

from engine.configuration import (
    AdaptiveConfig,
    EngineConfig,
    LibraryConfig,
    OutputConfig,
    parse_config,
    resolve_config_path,
)


class ConfigurationTests(unittest.TestCase):
    def test_parse_defaults_when_file_missing(self) -> None:
        config = parse_config(None)
        self.assertIsInstance(config, EngineConfig)
        self.assertEqual(config.library.clip_chars, LibraryConfig().clip_chars)
        self.assertEqual(config.output.prefix, OutputConfig().prefix)

    def test_parse_custom_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invitation.json"
            path.write_text(
                json.dumps(
                    {
                        "library": {"clip_chars": 100},
                        "output": {"prefix": "-- test --"},
                    }
                ),
                encoding="utf-8",
            )
            config = parse_config(path)
            self.assertEqual(config.library.clip_chars, 100)
            self.assertEqual(config.output.prefix, "-- test --")

    def test_resolve_config_path_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.json"
            path.write_text("{}", encoding="utf-8")
            try:
                os.environ["INVITATION_CONFIG"] = str(path)
                resolved = resolve_config_path(Path(tmp))
            finally:
                os.environ.pop("INVITATION_CONFIG", None)
            self.assertEqual(resolved, path)

    def test_adaptive_config_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invitation.json"
            path.write_text("{}", encoding="utf-8")
            adaptive = AdaptiveConfig(path)
            self.assertIsInstance(adaptive.snapshot(), EngineConfig)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
