import datetime as dt

import pytest

from zwo.parser import BLOCK_T, Duration, Percentage, Range, Tag
from zwo.serialize import BLOCK_MAPPING, _classify_ramp_type

THIRTY_SEC = dt.timedelta(seconds=30)
SAMPLE_RAMP_PARAMS = {
    Tag.DURATION: Duration(THIRTY_SEC),
    Tag.POWER: Range(Percentage(25), Percentage(50)),
}
SAMPLE_COOLDOWN_PARAMS = {
    Tag.DURATION: Duration(THIRTY_SEC),
    Tag.POWER: Range(Percentage(50), Percentage(25)),
}

RAMP_TEST_CASES = (
    (1, 3, SAMPLE_RAMP_PARAMS, BLOCK_MAPPING[Tag.WARMUP]),
    (2, 3, SAMPLE_RAMP_PARAMS, BLOCK_MAPPING[Tag.RAMP]),
    (3, 3, SAMPLE_RAMP_PARAMS, BLOCK_MAPPING[Tag.RAMP]),
    (3, 3, SAMPLE_COOLDOWN_PARAMS, BLOCK_MAPPING[Tag.COOLDOWN]),
    (1, 1, SAMPLE_RAMP_PARAMS, BLOCK_MAPPING[Tag.WARMUP]),
)


@pytest.mark.parametrize(("block_idx, n_blocks, block, truth_classification"), RAMP_TEST_CASES)
def test_ramp_classify(
    block_idx: int, n_blocks: int, block: BLOCK_T, truth_classification: str
) -> None:
    assert _classify_ramp_type(block_idx, n_blocks, block) == truth_classification
