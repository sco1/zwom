from collections import abc

from zwo.parser import BLOCK_T, Tag


class ZWOValidationError(BaseException):  # noqa: D101
    ...


class ZWOValidationWarning(Warning):  # noqa: D101
    ...


def validate_scanned(raw_blocks: list[BLOCK_T]) -> None:
    if Tag.META not in raw_blocks[0]:
        raise ZWOValidationError("ZWO file must begin with a META block")

    for block in raw_blocks[1:]:
        # Block dictionaries only have one key, so we can dispatch validators using the first key
        block_tag = next(iter(block))
        match block_tag:
            case Tag.FREE | Tag.SEGMENT:
                visit_segment_block(block, block_tag)
            case Tag.RAMP | Tag.WARMUP:
                visit_ramp_block(block, block_tag)
            case Tag.INTERVALS:
                visit_interval_block(block, block_tag)
            case _:
                raise ZWOValidationError(f"Unknown workout tag: '{block_tag}'")


def _check_keys(required: set[Tag], check_tags: abc.KeysView[Tag], block_tag: Tag) -> None:
    missing = required - check_tags
    if missing:
        pretty_tags = ", ".join(tag.upper() for tag in missing)
        raise ZWOValidationError(f"{block_tag.upper()} block missing required keys: {pretty_tags}")


def visit_meta_block(block: BLOCK_T, block_tag: Tag) -> None:
    params = block[block_tag]
    _check_keys({Tag.NAME, Tag.AUTHOR, Tag.DESCRIPTION}, params.keys(), block_tag)


def visit_segment_block(block: BLOCK_T, block_tag: Tag) -> None:
    params = block[block_tag]
    required_tags = {Tag.DURATION}
    if block_tag == Tag.SEGMENT:
        required_tags = required_tags | {Tag.POWER}

    _check_keys(required_tags, params.keys(), block_tag)


def visit_ramp_block(block: BLOCK_T, block_tag: Tag) -> None:
    params = block[block_tag]
    _check_keys({Tag.DURATION, Tag.POWER}, params.keys(), block_tag)


def visit_interval_block(block: BLOCK_T, block_tag: Tag) -> None:
    params = block[block_tag]
    _check_keys({Tag.COUNT, Tag.DURATION, Tag.POWER}, params.keys(), block_tag)
