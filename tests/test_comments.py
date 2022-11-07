import datetime as dt
from textwrap import dedent

from zwo.parser import Duration, Tag, parse_src


def test_single_line_block_comment() -> None:
    src = dedent(
        """\
        META {
            ; This is a comment!
            NAME "Foo",
            AUTHOR "sco1",
        }
        """
    )
    truth_block = {Tag.META: {Tag.NAME: "Foo", Tag.AUTHOR: "sco1"}, Tag.MESSAGES: None}

    assert parse_src(src)[0] == truth_block


def test_single_line_block_comment_inline() -> None:
    src = dedent(
        """\
        META {
            NAME "Foo", ; This is a comment!
            AUTHOR "sco1",
        }
        """
    )
    truth_block = {Tag.META: {Tag.NAME: "Foo", Tag.AUTHOR: "sco1"}, Tag.MESSAGES: None}

    assert parse_src(src)[0] == truth_block


def test_single_line_block_comment_tag() -> None:
    src = dedent(
        """\
        META {
            NAME "Foo",
            ; AUTHOR "sco1",
        }
        """
    )
    truth_block = {Tag.META: {Tag.NAME: "Foo"}, Tag.MESSAGES: None}

    assert parse_src(src)[0] == truth_block


def test_repeat_single_line_block_comment() -> None:
    src = dedent(
        """\
        META {
            ; In-block comment 1
            ; In-block comment 2
            NAME "Foo",
            AUTHOR "sco1",
        }
        """
    )
    truth_block = {Tag.META: {Tag.NAME: "Foo", Tag.AUTHOR: "sco1"}, Tag.MESSAGES: None}

    assert parse_src(src)[0] == truth_block


def test_multiple_single_line_block_comment() -> None:
    src = dedent(
        """\
        META {
            ; In-block comment 1
            NAME "Foo",
            ; In-block comment 2
            AUTHOR "sco1",
        }
        """
    )
    truth_block = {Tag.META: {Tag.NAME: "Foo", Tag.AUTHOR: "sco1"}, Tag.MESSAGES: None}

    assert parse_src(src)[0] == truth_block


def test_workout_level_comment() -> None:
    src = dedent(
        """\
        ; Workout comment
        META {
            NAME "Foo",
            AUTHOR "sco1",
        }
        """
    )
    truth_workout = [{Tag.META: {Tag.NAME: "Foo", Tag.AUTHOR: "sco1"}, Tag.MESSAGES: None}]

    assert parse_src(src) == truth_workout


def test_workout_repeat_comment() -> None:
    src = dedent(
        """\
        ; META {
        ;     NAME "Foo",
        ;     AUTHOR "sco1",
        ; }
        FREE {DURATION 04:20}
        """
    )
    truth_workout = [
        {Tag.FREE: {Tag.DURATION: Duration(dt.timedelta(seconds=260))}, Tag.MESSAGES: None}
    ]

    assert parse_src(src) == truth_workout


def test_workout_multiple_comment() -> None:
    src = dedent(
        """\
        ; META {
        ;     NAME "Foo",
        ;     AUTHOR "sco1",
        ; }
        FREE {DURATION 04:20}
        ; Workout comment
        """
    )
    truth_workout = [
        {Tag.FREE: {Tag.DURATION: Duration(dt.timedelta(seconds=260))}, Tag.MESSAGES: None}
    ]

    assert parse_src(src) == truth_workout


def test_mixed_level_comments() -> None:
    src = dedent(
        """\
        ; Workout comment
        META {
            NAME "Foo",
            ; In-block comment
            AUTHOR "sco1",
        }
        """
    )
    truth_workout = [{Tag.META: {Tag.NAME: "Foo", Tag.AUTHOR: "sco1"}, Tag.MESSAGES: None}]

    assert parse_src(src) == truth_workout
