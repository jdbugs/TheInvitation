import unittest

from engine.composer import ResponseComposer
from engine.configuration import ResponseConfig
from engine.library import SeedFragment


class StaticLibrary:
    def __init__(self, fragments):
        self._fragments = list(fragments)

    def pick(self, count, *, avoid=None):
        avoid = {item.strip() for item in avoid or set()}
        candidates = [frag for frag in self._fragments if frag.text.strip() not in avoid]
        pool = candidates if candidates else self._fragments
        return list(pool[:count])


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
        composer = ResponseComposer(  # type: ignore[arg-type]
            library,
            ResponseConfig(opening_line="Hello", closing_line="Goodbye."),
            oracle,
        )
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

    async def test_duplicate_fragments_are_collapsed(self) -> None:
        fragments = [
            SeedFragment(text="Repeat this.", source="a.txt"),
            SeedFragment(text="Repeat this.", source="b.txt"),
            SeedFragment(text="Another thought.", source="c.txt"),
        ]
        library = StaticLibrary(fragments)
        oracle = StubOracle(text=None)
        config = ResponseConfig(fragments=3, closing_line="")
        composer = ResponseComposer(library, config, oracle)  # type: ignore[arg-type]
        response = await composer.craft(user_text=None, channel="input")
        self.assertEqual(len(response.fragments), 2)
        self.assertIn("Repeat this.", response.text)
        self.assertIn("Another thought.", response.text)
        self.assertEqual(response.text.count("Repeat this."), 1)
        self.assertIn("\n\n", response.text)

    async def test_recent_fragment_memory_avoids_reuse(self) -> None:
        fragments = [
            SeedFragment(text="First", source="a.txt"),
            SeedFragment(text="Second", source="b.txt"),
        ]
        library = StaticLibrary(fragments)
        oracle = StubOracle(text=None)
        config = ResponseConfig(fragments=1, closing_line="", recent_fragment_window=2)
        composer = ResponseComposer(library, config, oracle)  # type: ignore[arg-type]
        first = await composer.craft(user_text="hi", channel="input")
        second = await composer.craft(user_text="again", channel="input")
        self.assertNotEqual(first.fragments[0].text, second.fragments[0].text)

    async def test_acknowledgement_template_uses_input(self) -> None:
        fragments = [SeedFragment(text="Fragment", source="a.txt")]
        library = StaticLibrary(fragments)
        oracle = StubOracle(text=None)
        config = ResponseConfig(
            fragments=1,
            closing_line="",
            acknowledgement_variants=("Listening: {input}",),
        )
        composer = ResponseComposer(library, config, oracle)  # type: ignore[arg-type]
        response = await composer.craft(user_text="echo", channel="input")
        self.assertIn("Listening: echo", response.text)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
