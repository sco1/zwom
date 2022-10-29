from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from xml.dom import minidom

from zwo.interpreter import ZWOMValidator
from zwo.parser import BLOCK_T, Message, PARAM_T, Percentage, PowerZone, Range, Tag

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
                for hashtag in val.split():
                    sub_tag = doc.createElement("tag")
                    sub_tag.setAttribute("name", hashtag.lstrip("#"))
                    tmp.appendChild(sub_tag)
            else:
                if tag == Tag.DESCRIPTION:
                    # Dedent the description to normalize any ZWOM indentation
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
            match block_tag:
                case Tag.FREE:
                    block_element = self.serialize_free(doc, block, block_tag)
                case Tag.SEGMENT:
                    block_element = self.serialize_segment(doc, block, block_tag)
                case Tag.RAMP | Tag.WARMUP | Tag.COOLDOWN:
                    zwift_key = _classify_ramp_type(idx, n_blocks)
                    block_element = self.serialize_ramp(doc, block, block_tag, zwift_key)
                case Tag.INTERVALS:
                    block_element = self.serialize_interval(doc, block, block_tag)
                case _:
                    ...

            if messages := block.get(Tag.MESSAGES):
                block_element = self.serialize_messages(doc, block_element, messages)

            workout.appendChild(block_element)

        return doc

    def serialize_free(
        self, doc: minidom.Document, block: BLOCK_T, block_tag: Tag
    ) -> minidom.Element:
        params = block[block_tag]
        block_element = doc.createElement(BLOCK_MAPPING[block_tag])
        block_element.setAttribute("Duration", str(params[Tag.DURATION]))
        block_element.setAttribute("FlatRoad", "0")

        return block_element

    def serialize_segment(
        self, doc: minidom.Document, block: BLOCK_T, block_tag: Tag
    ) -> minidom.Element:
        params = block[block_tag]
        block_element = doc.createElement(BLOCK_MAPPING[block_tag])
        block_element.setAttribute("Duration", str(params[Tag.DURATION]))
        block_element.setAttribute("Power", self.serialize_power(params[Tag.POWER]))
        block_element.setAttribute("pace", "0")

        return block_element

    def serialize_ramp(
        self, doc: minidom.Document, block: BLOCK_T, block_tag: Tag, zwift_key: str
    ) -> minidom.Element:
        params = block[block_tag]
        block_element = doc.createElement(zwift_key)
        block_element.setAttribute("Duration", str(params[Tag.DURATION]))

        power_range: Range = params[Tag.POWER]
        block_element.setAttribute("PowerLow", self.serialize_power(power_range.left))
        block_element.setAttribute("PowerHigh", self.serialize_power(power_range.right))
        block_element.setAttribute("pace", "0")

        return block_element

    def serialize_interval(
        self, doc: minidom.Document, block: BLOCK_T, block_tag: Tag
    ) -> minidom.Element:
        params = block[block_tag]
        block_element = doc.createElement(BLOCK_MAPPING[block_tag])
        block_element.setAttribute("Repeat", str(params[Tag.REPEAT]))

        duration_range: Range = params[Tag.DURATION]
        block_element.setAttribute("OnDuration", str(duration_range.left))
        block_element.setAttribute("OffDuration", str(duration_range.right))

        power_range: Range = params[Tag.POWER]
        block_element.setAttribute("PowerLow", self.serialize_power(power_range.left))
        block_element.setAttribute("PowerHigh", self.serialize_power(power_range.right))
        block_element.setAttribute("pace", "0")

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
