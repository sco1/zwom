import datetime as dt

import pytest

from zwo.interpreter import ZWOMValidationError, ZWOMValidator, _check_keys
from zwo.parser import BLOCK_T, Duration, PARAM_T, Percentage, Range, Tag

THIRTY_SEC = dt.timedelta(seconds=30)
THIRTY_SEC_DUR = Duration(THIRTY_SEC)
DUR_RANGE = Range(THIRTY_SEC_DUR, THIRTY_SEC_DUR)
POWER_PCT = Percentage(65)
POWER_RANGE_PCT = Range(Percentage(25), Percentage(50))
CADENCE_RANGE = Range(80, 120)


BLOCKS_META_NOT_FIRST = [
    {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR}},
    {Tag.META: {Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c"}},
]


def test_no_first_meta_raises() -> None:
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(BLOCKS_META_NOT_FIRST)


BAD_FTP_VALS = (
    ({Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c", Tag.FTP: 0},),
    ({Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c", Tag.FTP: THIRTY_SEC_DUR},),
)


@pytest.mark.parametrize(("meta_block",), BAD_FTP_VALS)
def test_bad_ftp_raises(meta_block: PARAM_T) -> None:
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator([{Tag.META: meta_block}])


GOOD_FTP_VALS = (
    ({Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c", Tag.FTP: 275}, 275),
    ({Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c"}, None),
)


@pytest.mark.parametrize(("meta_block", "truth_ftp"), GOOD_FTP_VALS)
def test_ftp_specified(meta_block: PARAM_T, truth_ftp: int | None) -> None:
    blocks = [{Tag.META: meta_block}]

    zv = ZWOMValidator(blocks)
    assert zv._ftp == truth_ftp


META_BLOCK = {Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c"}
META_BLOCK_MISSING = {Tag.NAME: "a", Tag.AUTHOR: "b"}


def test_check_keys() -> None:
    assert _check_keys({Tag.NAME, Tag.AUTHOR, Tag.DESCRIPTION}, META_BLOCK.keys(), Tag.META)


def test_check_keys_missing_raises() -> None:
    with pytest.raises(ZWOMValidationError):
        _check_keys({Tag.NAME, Tag.AUTHOR, Tag.DESCRIPTION}, META_BLOCK_MISSING.keys(), Tag.META)


RAMP_BLOCK = {Tag.DURATION: Duration(THIRTY_SEC), Tag.POWER: POWER_RANGE_PCT}


REQUIRED_KEY_CHECKS = (
    {Tag.FREE: {Tag.DURATION: THIRTY_SEC_DUR}},
    {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: Percentage(50)}},
    {Tag.INTERVALS: {Tag.REPEAT: 3, Tag.DURATION: DUR_RANGE, Tag.POWER: POWER_RANGE_PCT}},
    {Tag.WARMUP: RAMP_BLOCK},
    {Tag.RAMP: RAMP_BLOCK},
    {Tag.COOLDOWN: RAMP_BLOCK},
    {Tag.START_REPEAT: {Tag.REPEAT: 3}},
    {Tag.END_REPEAT: {}},
)


@pytest.mark.parametrize(("block"), REQUIRED_KEY_CHECKS)
def test_check_block_keys(block: BLOCK_T) -> None:
    block_tag = next(iter(block))
    if block_tag == Tag.START_REPEAT:
        blocks = [{Tag.META: META_BLOCK}, block, {Tag.END_REPEAT: {}}]
    elif block_tag == Tag.END_REPEAT:
        blocks = [{Tag.META: META_BLOCK}, {Tag.START_REPEAT: {Tag.REPEAT: 3}}, block]
    else:
        blocks = [{Tag.META: META_BLOCK}, block]

    ZWOMValidator(blocks)


def test_unknown_block_raises() -> None:
    blocks = [{Tag.META: META_BLOCK}, {Tag.AUTHOR: {Tag.DURATION: THIRTY_SEC_DUR}}]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_zero_power_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: 0}},
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_int_power_has_ftp() -> None:
    blocks = [
        {Tag.META: {Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c", Tag.FTP: 275}},
        {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: 150}},
    ]
    ZWOMValidator(blocks)


def test_int_power_no_ftp_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: 150}},
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_int_power_range_has_ftp() -> None:
    blocks = [
        {Tag.META: {Tag.NAME: "a", Tag.AUTHOR: "b", Tag.DESCRIPTION: "c", Tag.FTP: 275}},
        {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: Range(150, 250)}},
    ]
    ZWOMValidator(blocks)


def test_int_power_range_no_ftp_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {Tag.RAMP: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: Range(150, 250)}},
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_interval_cadence_nonrange_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {
            Tag.INTERVALS: {
                Tag.REPEAT: 3,
                Tag.DURATION: THIRTY_SEC_DUR,
                Tag.POWER: POWER_RANGE_PCT,
                Tag.CADENCE: 90,
            }
        },
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_cadence_range_noninterval_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {
            Tag.RAMP: {
                Tag.DURATION: THIRTY_SEC_DUR,
                Tag.POWER: POWER_RANGE_PCT,
                Tag.CADENCE: CADENCE_RANGE,
            }
        },
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_interval_cadence_range() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {
            Tag.INTERVALS: {
                Tag.REPEAT: 3,
                Tag.DURATION: THIRTY_SEC_DUR,
                Tag.POWER: POWER_RANGE_PCT,
                Tag.CADENCE: CADENCE_RANGE,
            }
        },
    ]
    ZWOMValidator(blocks)


def test_chunk_repeat() -> None:
    raw_blocks = [
        {Tag.META: META_BLOCK},
        {Tag.START_REPEAT: {Tag.REPEAT: 2}},
        {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: POWER_PCT}},
        {Tag.END_REPEAT: {}},
    ]

    truth_blocks = [
        {Tag.META: META_BLOCK},
        {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: POWER_PCT}},
        {Tag.SEGMENT: {Tag.DURATION: THIRTY_SEC_DUR, Tag.POWER: POWER_PCT}},
    ]

    val = ZWOMValidator(raw_blocks)
    assert val.validated_blocks == truth_blocks


def test_nested_chunk_repeat_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {Tag.START_REPEAT: {Tag.REPEAT: 2}},
        {Tag.START_REPEAT: {Tag.REPEAT: 2}},
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_missing_end_repeat_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {Tag.START_REPEAT: {Tag.REPEAT: 2}},
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


BAD_REPEATS = (
    ({Tag.START_REPEAT: {Tag.REPEAT: 0}},),
    ({Tag.START_REPEAT: {Tag.REPEAT: CADENCE_RANGE}},),
)


@pytest.mark.parametrize(("start_block",), BAD_REPEATS)
def test_bad_chunk_repeat_val_raises(start_block: BLOCK_T) -> None:
    blocks = [{Tag.META: META_BLOCK}, start_block, {Tag.END_REPEAT: {}}]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)


def test_chunk_repeat_end_no_start_raises() -> None:
    blocks = [
        {Tag.META: META_BLOCK},
        {Tag.END_REPEAT: {}},
    ]
    with pytest.raises(ZWOMValidationError):
        ZWOMValidator(blocks)
