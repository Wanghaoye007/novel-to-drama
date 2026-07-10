import pytest

from novel_drama_engine.demo import demo_haomen_source, demo_round_outputs


@pytest.fixture
def happy_round_outputs():
    return demo_round_outputs(source_text=demo_haomen_source())
