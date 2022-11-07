from __future__ import annotations

import datetime as dt
import typing as t
from collections import deque
from dataclasses import dataclass
from enum import Enum, StrEnum, auto
from textwrap import dedent

from parsimonious.grammar import Grammar
from parsimonious.nodes import Node, NodeVisitor

RAW_GRAMMAR = r"""
    workout   = ((comment / block) elws*)+ / elws
    block     = tag ws "{" ((comment / params) / elws)+ "}"
    params    = (message / value) ","?
    value     = tag ws (string / range / rangeval)

    message   = "@" ws duration ws string
    range     = rangeval ws "->" ws rangeval
    rangeval  = duration / numeric / zone
    duration  = number ":" number
    percent   = number "%"
    zone      = ("Z" number) / "SS"
    numeric   = percent / number
    elws      = ws / emptyline

    comment   = ~r"\;[^\r\n]*"
    tag       = ~"[A-Z_]+"
    string    = ~'"[^\"]+"'
    number    = ~"\d+"
    ws        = ~"\s*"
    emptyline = ws+
    """
GRAMMAR = Grammar(RAW_GRAMMAR)


class Tag(StrEnum):
    AUTHOR = auto()
    CADENCE = auto()
    COOLDOWN = auto()
    DESCRIPTION = auto()
    DURATION = auto()
    FREE = auto()
    FTP = auto()
    INTERVALS = auto()
    META = auto()
    NAME = auto()
    POWER = auto()
    RAMP = auto()
    REPEAT = auto()
    SEGMENT = auto()
    TAGS = auto()
    WARMUP = auto()

    MESSAGES = auto()  # Included for tidier housekeeping, not a valid keyword in the ZWO file

    # Repeat segment metasyntax
    START_REPEAT = auto()
    END_REPEAT = auto()


@dataclass(frozen=True, slots=True)
class Percentage:
    value: int

    def __str__(self) -> str:
        return f"{self.value / 100:0.3f}"

    @classmethod
    def from_node(cls, node: Node) -> Percentage:
        return cls(value=int(node.text.rstrip("%")))


class PowerZone(Enum):
    Z1 = Percentage(value=50)
    Z2 = Percentage(value=65)
    Z3 = Percentage(value=81)
    SS = Percentage(value=90)
    Z4 = Percentage(value=95)
    Z5 = Percentage(value=109)
    Z6 = Percentage(value=125)
    Z7 = Percentage(value=150)

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class Duration:
    value: dt.timedelta

    def __str__(self) -> str:
        return str(int(self.value.total_seconds()))

    @classmethod
    def from_node(cls, node: Node) -> Duration:
        minutes, seconds = (int(chunk) for chunk in node.text.split(":"))
        return cls(value=dt.timedelta(minutes=minutes, seconds=seconds))


RANGE_T = Percentage | Duration | PowerZone | int


@dataclass(frozen=True, slots=True)
class Range:
    left: RANGE_T
    right: RANGE_T

    @classmethod
    def from_node(cls, visited_children: list[Node]) -> Range:
        left, *_, right = visited_children

        # I'm not sure how to best keep the numeric values from nesting, I might be misunderstanding
        # how the parser is working or have something written poorly in the grammar but for now this
        # hack functions
        if isinstance(left, list):
            left = left[0]
        if isinstance(right, list):
            right = right[0]

        return cls(left=left, right=right)


@dataclass(frozen=True, slots=True)
class Message:
    timestamp: Duration
    message: str

    @classmethod
    def from_node(cls, visited_children: list[Node]) -> Message:
        _, _, timestamp, _, message = visited_children
        return cls(timestamp=timestamp, message=message)


T = t.TypeVar("T")


def deep_flatten(in_iter: list, key_type: type[T]) -> t.Generator[T, None, None]:
    """Accept an arbitrary list of lists and yield objects of the matching data type."""
    # Use a deque as an iterator stack to keep track of any nested iterables
    iterators = deque((iter(in_iter),))

    # Iterate over the elements of each iterable & add them to the stack if they're also a list,
    # otherwise yield only dicts & then pop the iterable once exhausted
    while iterators:
        for item in iterators[-1]:
            if isinstance(item, list):
                iterators.append(iter(item))
                break
            elif isinstance(item, key_type):
                yield item
        else:
            iterators.pop()


VAL_T = int | str | Percentage | Duration | Range | list[Message] | None
PARAM_T = dict[Tag, VAL_T]
BLOCK_T = dict[Tag, PARAM_T]


class ZWOVisitor(NodeVisitor):

    grammar = GRAMMAR

    # Indices of visited_children are determined by the grammar specification
    def visit_workout(self, node: Node, visited_children: list[Node]) -> list[BLOCK_T]:
        # Catch an empty document
        if not node.text.strip():
            return []

        blocks = []
        for chunk in visited_children[0]:
            # The grammar here matches comments or blocks, if there are no dictionaries then we
            # have a comment, which we just discard
            if block := list(deep_flatten(chunk, key_type=dict)):
                blocks.append(block[0])

        return blocks

    def visit_block(self, node: Node, visited_children: list[Node]) -> BLOCK_T:
        tag = visited_children[0]
        params = list(deep_flatten(visited_children[-2], key_type=dict))
        block_messages = list(deep_flatten(visited_children[-2], key_type=Message))

        block_params: BLOCK_T = {tag: {key: val for param in params for key, val in param.items()}}
        block_params[Tag.MESSAGES] = block_messages if block_messages else None  # type: ignore[assignment]  # noqa: E501

        return block_params

    def visit_value(self, node: Node, visited_children: list[Node]) -> PARAM_T:
        tag, _, value = visited_children

        # I'm not sure how to best keep the numeric values from nesting, I might be misunderstanding
        # how the parser is working or have something written poorly in the grammar but for now this
        # hack functions
        val = value[0]
        if isinstance(val, list):
            val = val[0]

        return {tag: val}

    def visit_string(self, node: Node, visited_children: list[Node]) -> str:
        return dedent(node.text.strip('"'))

    def visit_range(self, node: Node, visited_children: list[Node]) -> Range:
        return Range.from_node(visited_children)

    def visit_duration(self, node: Node, visited_children: list[Node]) -> Duration:
        return Duration.from_node(node)

    def visit_tag(self, node: Node, visited_children: list[Node]) -> Tag:
        return Tag[node.text]

    def visit_message(self, node: Node, visited_children: list[Node]) -> Message:
        return Message.from_node(visited_children)

    def visit_numeric(self, node: Node, visited_children: list[Node]) -> int | Percentage:
        return visited_children[0]  # type: ignore[no-any-return]

    def visit_number(self, node: Node, visited_children: list[Node]) -> int:
        return int(node.text)

    def visit_percent(self, node: Node, visited_children: list[Node]) -> Percentage:
        return Percentage.from_node(node)

    def visit_zone(self, node: Node, visited_children: list[Node]) -> PowerZone:
        return PowerZone[node.text]

    def generic_visit(self, node: Node, visited_children: list[Node]) -> list[Node] | Node:
        return visited_children or node


def parse_src(src: str) -> list[BLOCK_T]:
    """Parse the provided source into a list of raw workout blocks."""
    tree = ZWOVisitor.grammar.parse(src)
    visitor = ZWOVisitor()
    parsed: list[BLOCK_T] = visitor.visit(tree)
    return parsed
