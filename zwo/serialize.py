from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from xml.dom import minidom

from zwo.interpreter import ZWOMValidator
from zwo.parser import BLOCK_T, Duration, Message, PARAM_T, Percentage, PowerZone, Range, Tag

STATIC_META_PARAMS = {"sportType": "bike"}

BLOCK_MAPPING = {
    Tag.COOLDOWN: "Cooldown",
    Tag.FREE: "FreeRide",
    Tag.INTERVALS: "IntervalsT",
    Tag.RAMP: "Ramp",
    Tag.SEGMENT: "SteadyState",
    Tag.WARMUP: "WarmUp",
}


@dataclass(slots=True)
class Workout:
    raw_blocks: list[BLOCK_T]

    _ftp: int | None = None

    def __post_init__(self) -> None:
        val = ZWOMValidator(self.raw_blocks)
        self._ftp = val._ftp

    def to_zwo(self, out_filepath: Path) -> None:
        doc = minidom.Document()
        root = doc.createElement("workout_file")
        doc.appendChild(root)

        # If we're here then we've validate that the meta tag is the first block
        doc = self.serialize_meta(doc, root, self.raw_blocks[0][Tag.META])
        doc = self.serialize_workout_blocks(doc, root, self.raw_blocks[1:])

        print(doc.toprettyxml())

    def serialize_meta(
        self, doc: minidom.Document, root: minidom.Element, meta_block: PARAM_T
    ) -> minidom.Document:
        for tag, val in meta_block.items():
            if tag == Tag.FTP:
                continue

            tmp = doc.createElement(tag)
            if tag == Tag.TAGS:
                if not isinstance(val, str):
                    raise ValueError("Type narrowing, shouldn't be able to get here")

                for hashtag in val.split():
                    sub_tag = doc.createElement("tag")
                    sub_tag.setAttribute("name", hashtag.lstrip("#"))
                    tmp.appendChild(sub_tag)
            else:
                if tag == Tag.DESCRIPTION:
                    if not isinstance(val, str):
                        raise ValueError("Type narrowing, shouldn't be able to get here")

                    val = dedent(val)

                tmp.appendChild(doc.createTextNode(val))

            root.appendChild(tmp)

        # Add any remaining static parameters that Zwift is expecting
        for element, val in STATIC_META_PARAMS.items():
            tmp = doc.createElement(element)
            tmp.appendChild(doc.createTextNode(val))
            root.appendChild(tmp)

        return doc

    def serialize_workout_blocks(
        self, doc: minidom.Document, root: minidom.Element, blocks: list[BLOCK_T]
    ) -> minidom.Document:
        workout = doc.createElement("workout")
        root.appendChild(workout)

        n_blocks = len(blocks)
        for idx, block in enumerate(blocks, start=1):
            # Blocks only have one key, so we can dispatch serializers using the first key
            block_tag = next(iter(block))
            params = block[block_tag]
            match block_tag:
                case Tag.FREE:
                    block_element = self._build_simple_block(
                        doc, BLOCK_MAPPING[block_tag], params, add_flat_road=True
                    )
                case Tag.SEGMENT:
                    block_element = self._build_simple_block(
                        doc, BLOCK_MAPPING[block_tag], params, add_power=True, add_pace=True
                    )
                case Tag.RAMP | Tag.WARMUP | Tag.COOLDOWN:
                    zwift_key = _classify_ramp_type(idx, n_blocks)
                    block_element = self._build_simple_block(doc, zwift_key, params, add_pace=True)
                    block_element = self.serialize_ramp(block_element, params)
                case Tag.INTERVALS:
                    block_element = self._build_simple_block(
                        doc, BLOCK_MAPPING[block_tag], params, add_duration=False, add_pace=True
                    )
                    block_element = self.serialize_interval(block_element, params)
                case _:
                    ...

            if messages := block.get(Tag.MESSAGES):
                if not isinstance(messages, list):
                    raise ValueError("Type narrowing, shouldn't be able to get here")

                block_element = self.serialize_messages(doc, block_element, messages)

            workout.appendChild(block_element)

        return doc

    def _build_simple_block(
        self,
        doc: minidom.Document,
        zwift_key: str,
        params: PARAM_T,
        add_duration: bool = True,
        add_power: bool = False,
        add_flat_road: bool = False,
        add_pace: bool = False,
    ) -> minidom.Element:
        block_element: minidom.Element = doc.createElement(zwift_key)

        if add_duration:
            block_element.setAttribute("Duration", str(params[Tag.DURATION]))

        if add_power:
            power = params[Tag.POWER]
            if not isinstance(power, (int, Percentage, PowerZone)):
                raise ValueError("Type narrowing, shouldn't be able to get here")

            block_element.setAttribute("Power", self.serialize_power(power))

        if add_flat_road:
            block_element.setAttribute("FlatRoad", "0")

        if add_pace:
            block_element.setAttribute("pace", "0")

        return block_element

    def serialize_ramp(self, block_element: minidom.Element, params: PARAM_T) -> minidom.Element:
        power_range = params[Tag.POWER]
        if not isinstance(power_range, Range):
            raise ValueError("Type narrowing, shouldn't be able to get here")

        if isinstance(power_range.left, Duration) or isinstance(power_range.right, Duration):
            raise ValueError("Type narrowing, shouldn't be able to get here")

        block_element.setAttribute("PowerLow", self.serialize_power(power_range.left))
        block_element.setAttribute("PowerHigh", self.serialize_power(power_range.right))

        return block_element

    def serialize_interval(
        self, block_element: minidom.Element, params: PARAM_T
    ) -> minidom.Element:
        block_element.setAttribute("Repeat", str(params[Tag.REPEAT]))

        duration_range = params[Tag.DURATION]
        if not isinstance(duration_range, Range):
            raise ValueError("Type narrowing, shouldn't be able to get here")

        block_element.setAttribute("OnDuration", str(duration_range.left))
        block_element.setAttribute("OffDuration", str(duration_range.right))

        power_range = params[Tag.POWER]
        if not isinstance(power_range, Range):
            raise ValueError("Type narrowing, shouldn't be able to get here")

        if isinstance(power_range.left, Duration) or isinstance(power_range.right, Duration):
            raise ValueError("Type narrowing, shouldn't be able to get here")

        block_element.setAttribute("PowerLow", self.serialize_power(power_range.left))
        block_element.setAttribute("PowerHigh", self.serialize_power(power_range.right))

        return block_element

    def serialize_messages(
        self, doc: minidom.Document, root: minidom.Element, messages: list[Message]
    ) -> minidom.Element:
        for message in messages:
            msg = doc.createElement("textevent")
            msg.setAttribute("timeoffset", str(message.timestamp))
            msg.setAttribute("message", message.message)

            root.appendChild(msg)

        return root

    def serialize_power(self, power: int | Percentage | PowerZone) -> str:
        if isinstance(power, int):
            if self._ftp is None:
                raise ValueError("Type narrowing, shouldn't be able to get here")

            return str(power / self._ftp)
        else:
            return str(power)


def _classify_ramp_type(block_idx: int, n_blocks: int) -> str:
    """
    Locate the appropriate Zwift block tag for the provided ramp block location.

    While there is no specific Ramp block in the workout building UI, some experimental observations
    have been made:
        * If a ramp is at the very beginning of the workout, Zwift serializes it as a Warmup block
        * If there are multiple blocks in a workout and a ramp is at the end, Zwift serializes it
        as a Cooldown block
        * If there are multiple blocks in a workout and a ramp is not at the beginning or the end,
        Zwift serializes it as a Ramp block
    """
    if block_idx == 1:
        return BLOCK_MAPPING[Tag.WARMUP]
    if block_idx == n_blocks:
        return BLOCK_MAPPING[Tag.COOLDOWN]
    else:
        return BLOCK_MAPPING[Tag.RAMP]
