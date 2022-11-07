import datetime as dt
from textwrap import dedent

import pytest

from zwo.parser import Duration, Message, Percentage, PowerZone, Range, Tag, VAL_T, parse_src

SAMPLE_DURATION = Duration(dt.timedelta(seconds=666))
SAMPLE_POWER_PER = Percentage(value=65)
SAMPLE_POWER_Z = PowerZone.Z1
SAMPLE_RANGE_DURATION = Range(
    left=Duration(dt.timedelta(seconds=30)), right=Duration(dt.timedelta(seconds=45))
)
SAMPLE_RANGE_POWER_W = Range(left=120, right=420)
SAMPLE_RANGE_POWER_PER = Range(left=Percentage(65), right=Percentage(100))
SAMPLE_RANGE_POWER_Z = Range(left=PowerZone.Z1, right=PowerZone.Z3)
SAMPLE_MESSAGE = Message(timestamp=SAMPLE_DURATION, message="Yo quiero Taco Bell")


# Just use a FREE block for convenience, this isn't going to validation
VAL_BLOCKS = (
    ("FREE {DURATION 11:06}", Tag.DURATION, SAMPLE_DURATION),
    ("FREE {DURATION 00:30 -> 00:45}", Tag.DURATION, SAMPLE_RANGE_DURATION),
    ("FREE {POWER 65%}", Tag.POWER, SAMPLE_POWER_PER),
    ("FREE {POWER Z1}", Tag.POWER, SAMPLE_POWER_Z),
    ("FREE {POWER SS}", Tag.POWER, PowerZone.SS),
    ("FREE {POWER 165}", Tag.POWER, 165),
    ("FREE {POWER 120 -> 420}", Tag.POWER, SAMPLE_RANGE_POWER_W),
    ("FREE {POWER 65% -> 100%}", Tag.POWER, SAMPLE_RANGE_POWER_PER),
    ("FREE {POWER Z1 -> Z3}", Tag.POWER, SAMPLE_RANGE_POWER_Z),
    ('FREE {DESCRIPTION "Yo quiero Taco Bell"}', Tag.DESCRIPTION, "Yo quiero Taco Bell"),
    ('FREE {@ 11:06 "Yo quiero Taco Bell"}', Tag.MESSAGES, [SAMPLE_MESSAGE]),
)


@pytest.mark.parametrize(("src", "param_tag", "truth_val"), VAL_BLOCKS)
def test_value_conversion(src: str, param_tag: Tag, truth_val: VAL_T) -> None:
    block = parse_src(src)[0]

    if param_tag == Tag.MESSAGES:
        # Messages are indexed from the root of the block
        assert block[Tag.MESSAGES] == truth_val
    else:
        assert block[Tag.FREE][param_tag] == truth_val


STR_OBJS = (
    (SAMPLE_POWER_PER, "0.650"),
    (SAMPLE_POWER_Z, "0.500"),
    (SAMPLE_DURATION, "666"),
)


@pytest.mark.parametrize(("obj", "truth_str"), STR_OBJS)
def test_str_methods(obj: Percentage | PowerZone | Duration, truth_str: str) -> None:
    assert str(obj) == truth_str


EMPTY_SRC = (
    ("",),
    (" ",),
    ("\n",),
    ("\n ",),
    (" \n ",),
    (" \n  \n",),
)


@pytest.mark.parametrize(("src",), EMPTY_SRC)
def test_empty_file_ok(src: str) -> None:
    assert parse_src(src) == []


BLOCK_SINGLE_PARAM = (
    ("FREE {DURATION 11:06}",),
    ("FREE {DURATION 11:06,}",),
    (
        dedent(
            """\
            FREE {
                DURATION 11:06
            }
            """
        ),
    ),
    (
        dedent(
            """\
            FREE {
                DURATION 11:06,
            }
            """
        ),
    ),
)
TRUTH_SINGLE_BLOCK_SINGLE_PARAM = [{Tag.FREE: {Tag.DURATION: SAMPLE_DURATION}, Tag.MESSAGES: None}]


@pytest.mark.parametrize(("src",), BLOCK_SINGLE_PARAM)
def test_block_single_param(src: str) -> None:
    assert parse_src(src) == TRUTH_SINGLE_BLOCK_SINGLE_PARAM


BLOCK_MULTI_PARAM = (
    ("SEGMENT {DURATION 11:06, POWER 65%}",),
    ("SEGMENT {DURATION 11:06, POWER 65%,}",),
    (
        dedent(
            """\
            SEGMENT {
                DURATION 11:06, POWER 65%
            }
            """
        ),
    ),
    (
        dedent(
            """\
            SEGMENT {
                DURATION 11:06, POWER 65%,
            }
            """
        ),
    ),
    (
        dedent(
            """\
            SEGMENT {
                DURATION 11:06,
                POWER 65%
            }
            """
        ),
    ),
    (
        dedent(
            """\
            SEGMENT {
                DURATION 11:06,
                POWER 65%,
            }
            """
        ),
    ),
)
TRUTH_SINGLE_BLOCK_MULTI_PARAM = [
    {Tag.SEGMENT: {Tag.DURATION: SAMPLE_DURATION, Tag.POWER: SAMPLE_POWER_PER}, Tag.MESSAGES: None}
]


@pytest.mark.parametrize(("src",), BLOCK_MULTI_PARAM)
def test_block_multi_param(src: str) -> None:
    assert parse_src(src) == TRUTH_SINGLE_BLOCK_MULTI_PARAM


def test_multi_block() -> None:
    src = dedent(
        """\
        FREE {DURATION 11:06}
        SEGMENT {DURATION 11:06, POWER 65%}
        """
    )
    truth_blocks = [
        {Tag.FREE: {Tag.DURATION: SAMPLE_DURATION}, Tag.MESSAGES: None},
        {
            Tag.SEGMENT: {Tag.DURATION: SAMPLE_DURATION, Tag.POWER: SAMPLE_POWER_PER},
            Tag.MESSAGES: None,
        },
    ]
    assert parse_src(src) == truth_blocks


def test_block_with_multiline_description() -> None:
    src = dedent(
        """\
        META {
            DESCRIPTION "Yo quiero
        Taco Bell",
        }
        """
    )
    truth_block = {Tag.META: {Tag.DESCRIPTION: "Yo quiero\nTaco Bell"}, Tag.MESSAGES: None}
    assert parse_src(src)[0] == truth_block


def test_segment_with_message() -> None:
    src = dedent(
        """\
        FREE {
            DURATION 11:06,
            @ 11:06 "Yo quiero Taco Bell",
        }
        """
    )
    truth_block = {Tag.FREE: {Tag.DURATION: SAMPLE_DURATION}, Tag.MESSAGES: [SAMPLE_MESSAGE]}
    assert parse_src(src)[0] == truth_block


def test_segment_with_leading_message() -> None:
    src = dedent(
        """\
        FREE {
            @ 11:06 "Yo quiero Taco Bell",
            DURATION 11:06,
        }
        """
    )
    truth_block = {Tag.FREE: {Tag.DURATION: SAMPLE_DURATION}, Tag.MESSAGES: [SAMPLE_MESSAGE]}
    assert parse_src(src)[0] == truth_block


def test_segment_with_multiline_message() -> None:
    src = dedent(
        """\
        FREE {
            DURATION 11:06,
            @ 11:06 "Yo quiero
        Taco Bell",
        }
        """
    )
    msg = Message(timestamp=SAMPLE_DURATION, message="Yo quiero\nTaco Bell")
    truth_block = {Tag.FREE: {Tag.DURATION: SAMPLE_DURATION}, Tag.MESSAGES: [msg]}
    assert parse_src(src)[0] == truth_block


def test_underscore_in_tag() -> None:
    src = dedent(
        """\
        START_REPEAT {REPEAT 3}
        """
    )
    truth_block = {Tag.START_REPEAT: {Tag.REPEAT: 3}, Tag.MESSAGES: None}
    assert parse_src(src)[0] == truth_block
