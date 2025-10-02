from __future__ import annotations

from pathlib import Path
import asyncio
import json
import os
import tempfile
import unittest

from engine.configuration import AdaptiveConfig, EngineConfig, FieldConfig, resolve_config_path


class ConfigurationTests(unittest.TestCase):
    def test_snapshot_includes_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "invitation.json"
            config_path.write_text(json.dumps({"field": {"clip": 300}}), encoding="utf-8")
            adaptive = AdaptiveConfig(config_path)
            snapshot = adaptive.snapshot()
            self.assertIsInstance(snapshot, EngineConfig)
            self.assertEqual(snapshot.field.clip, 300)
            self.assertGreater(len(snapshot.weave.architectures), 0)

    def test_watch_applies_updates(self) -> None:
        async def scenario() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                config_path = Path(tmp) / "invitation.json"
                config_path.write_text(json.dumps({"field": {"clip": 360}}), encoding="utf-8")
                adaptive = AdaptiveConfig(config_path)
                seen: list[int] = []

                def listener(config: EngineConfig) -> None:
                    seen.append(config.field.clip)

                adaptive.add_listener(listener)
                task = asyncio.create_task(adaptive.watch(interval=0.2))
                await asyncio.sleep(0.3)
                config_path.write_text(json.dumps({"field": {"clip": 280}}), encoding="utf-8")
                await asyncio.sleep(0.5)
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task
            return seen

        import contextlib

        seen = asyncio.run(scenario())
        self.assertIn(280, seen)

    def test_resolve_config_path_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            custom = Path(tmp) / "custom.json"
            custom.write_text("{}", encoding="utf-8")
            try:
                os.environ["INVITATION_CONFIG"] = str(custom)
                resolved = resolve_config_path(Path("."))
            finally:
                os.environ.pop("INVITATION_CONFIG", None)
            self.assertEqual(resolved, custom)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
