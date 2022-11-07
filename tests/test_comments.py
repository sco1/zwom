from textwrap import dedent

from zwo.parser import Tag, parse_src


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
            ; Comment line 1
            ; Comment line 2
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
            ; Comment line 1
            NAME "Foo",
            ; Comment line 2
            AUTHOR "sco1",
        }
        """
    )
    truth_block = {Tag.META: {Tag.NAME: "Foo", Tag.AUTHOR: "sco1"}, Tag.MESSAGES: None}

    assert parse_src(src)[0] == truth_block
