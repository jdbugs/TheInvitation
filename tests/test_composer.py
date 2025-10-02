import unittest

from engine.composer import ResponseComposer
from engine.configuration import ResponseConfig
from engine.library import SeedFragment


class StaticLibrary:
    def __init__(self, fragments):
        self._fragments = list(fragments)

    def pick(self, count):
        return list(self._fragments[:count])


class StubOracle:
    def __init__(self, text: str | None) -> None:
        self._text = text
        self.calls = 0

    @property
    def enabled(self) -> bool:
        return self._text is not None

    async def generate(self, prompt: str) -> str | None:
        self.calls += 1
        return self._text


class ComposerTests(unittest.IsolatedAsyncioTestCase):
    async def test_compose_with_echo_and_closing_line(self) -> None:
        fragments = [SeedFragment(text="A small fragment.", source="a.txt")]
        library = StaticLibrary(fragments)
        oracle = StubOracle(text=None)
        composer = ResponseComposer(library, ResponseConfig(opening_line="Hello", closing_line="Goodbye."), oracle)  # type: ignore[arg-type]
        response = await composer.craft(user_text="Who are you?", channel="input")
        self.assertIn("You said: Who are you?", response.text)
        self.assertTrue(response.text.endswith("Goodbye."))
        self.assertFalse(response.used_oracle)

    async def test_compose_with_oracle(self) -> None:
        fragments = [SeedFragment(text="First", source="a.txt"), SeedFragment(text="Second", source="b.txt")]
        library = StaticLibrary(fragments)
        oracle = StubOracle(text="Oracle whisper.")
        config = ResponseConfig(max_chars=120, oracle_probability=1.0, closing_line="")
        composer = ResponseComposer(library, config, oracle)  # type: ignore[arg-type]
        response = await composer.craft(user_text=None, channel="silence")
        self.assertTrue(response.used_oracle)
        self.assertIn("Oracle whisper.", response.text)
        self.assertLessEqual(len(response.text), config.max_chars)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
