from __future__ import annotations

import datetime as dt
import typing as t
from collections import deque
from dataclasses import dataclass
from enum import StrEnum, auto

from parsimonious.grammar import Grammar
from parsimonious.nodes import Node, NodeVisitor

RAW_GRAMMAR = r"""
    workout   = (block elws*)+ emptyline*
    block     = tag ws "{" (((message / value) ","?) / elws)+ "}"
    value     = tag ws (string / range / rangeval)

    message   = "@" ws duration ws string
    range     = rangeval ws "->" ws rangeval
    rangeval  = (duration / numeric)

    duration  = number ":" number
    percent   = number "%"
    numeric   = (percent / number)
    elws      = (ws / emptyline)

    tag       = ~"[A-Z]+"
    string    = ~'"[^\"]+"'
    number    = ~"\d+"
    ws        = ~"\s*"
    emptyline = ws+
    """
GRAMMAR = Grammar(RAW_GRAMMAR)


class Tag(StrEnum):
    AUTHOR = auto()
    CADENCE = auto()
    COUNT = auto()
    DESCRIPTION = auto()
    DURATION = auto()
    FREE = auto()
    FTP = auto()
    INTERVALS = auto()
    META = auto()
    NAME = auto()
    POWER = auto()
    RAMP = auto()
    SEGMENT = auto()
    TAGS = auto()
    WARMUP = auto()

    MESSAGES = auto()  # Included for tidier housekeeping, not a valid keyword in the ZWO file


@dataclass(frozen=True, slots=True)
class Percentage:
    value: int

    @classmethod
    def from_node(cls, node: Node) -> Percentage:
        return cls(value=int(node.text.rstrip("%")))


@dataclass(frozen=True, slots=True)
class Duration:
    value: dt.timedelta

    @classmethod
    def from_node(cls, node: Node) -> Duration:
        minutes, seconds = (int(chunk) for chunk in node.text.split(":"))
        return cls(value=dt.timedelta(minutes=minutes, seconds=seconds))


RANGE_T = Percentage | Duration | int


@dataclass(frozen=True, slots=True)
class Range:
    left: RANGE_T
    right: RANGE_T

    @classmethod
    def from_node(cls, visited_children: list[Node]) -> Range:
        left, *_, right = visited_children
        return cls(left=left, right=right)


@dataclass(frozen=True, slots=True)
class Message:
    timestamp: dt.datetime
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


VAL_T = int | str | Percentage | Duration | Range
PARAM_T = dict[Tag, VAL_T]
BLOCK_T = dict[Tag, PARAM_T | list[Message] | None]


class ZWOVisitor(NodeVisitor):

    grammar = GRAMMAR

    def visit_workout(self, node: Node, visited_children: list[Node]) -> list[BLOCK_T]:
        blocks, *_ = visited_children

        return [block[0] for block in blocks]

    def visit_block(self, node: Node, visited_children: list[Node]) -> BLOCK_T:
        tag = visited_children[0]
        # Can this index be relied on?
        params = list(deep_flatten(visited_children[-2], key_type=dict))
        block_messages = list(deep_flatten(visited_children[-2], key_type=Message))

        block_params: BLOCK_T = {tag: {key: val for param in params for key, val in param.items()}}
        block_params[Tag.MESSAGES] = block_messages if block_messages else None

        return block_params

    def visit_value(self, node: Node, visited_children: list[Node]) -> PARAM_T:
        tag, _, value, *_ = visited_children
        return {tag: value[0]}  # With the current grammar there shouldn't be any value nesting

    def visit_string(self, node: Node, visited_children: list[Node]) -> str:
        return node.text.strip('"')  # type: ignore[no-any-return]

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

    def generic_visit(self, node: Node, visited_children: list[Node]) -> list[Node] | Node:
        return visited_children or node
