from collections import abc
from dataclasses import dataclass

from zwo.parser import BLOCK_T, PARAM_T, Range, Tag, VAL_T


class ZWOMValidationError(BaseException):  # noqa: D101
    ...


def _check_keys(required: set[Tag], check_tags: abc.KeysView[Tag], block_tag: Tag) -> bool:
    missing = required - check_tags
    if missing:
        pretty_tags = ", ".join(tag.upper() for tag in missing)
        raise ZWOMValidationError(f"{block_tag.upper()} block missing required keys: {pretty_tags}")

    return True


@dataclass(slots=True)
class ZWOMValidator:
    raw_blocks: list[BLOCK_T]

    _ftp: int | None = None

    def __post_init__(self) -> None:
        self.validate_scanned()

    def validate_scanned(self) -> None:
        if Tag.META not in self.raw_blocks[0]:
            raise ZWOMValidationError("ZWOM file must begin with a META block")

        self.visit_meta_block(self.raw_blocks[0][Tag.META], Tag.META)

        for block in self.raw_blocks[1:]:
            # Blocks only have one key, so we can dispatch validators using the first key
            block_tag = next(iter(block))
            params = block[block_tag]
            match block_tag:
                case Tag.FREE | Tag.SEGMENT:
                    self.visit_segment_block(params, block_tag)
                case Tag.RAMP | Tag.WARMUP | Tag.COOLDOWN:
                    self.visit_ramp_block(params, block_tag)
                case Tag.INTERVALS:
                    self.visit_interval_block(params, block_tag)
                case _:
                    raise ZWOMValidationError(f"Unknown workout tag: '{block_tag}'")

            # Dispatch any additional generic parameter validation within the block
            for param, val in params.items():
                match param:
                    case Tag.POWER:
                        self.visit_power(val)
                    case Tag.CADENCE:
                        self.visit_cadence(val, block_tag)
                    case _:
                        continue

    def visit_meta_block(self, params: PARAM_T, block_tag: Tag) -> None:
        required_tags = {Tag.NAME, Tag.AUTHOR, Tag.DESCRIPTION}
        _check_keys(required_tags, params.keys(), block_tag)

        ftp = params.get(Tag.FTP)
        if ftp is not None:
            if isinstance(ftp, int):
                if ftp == 0:  # The parser already won't accept negative numbers
                    raise ZWOMValidationError(f"FTP must be > 0, received: {ftp}")

                self._ftp = ftp
            else:
                raise ZWOMValidationError(
                    f"FTP must be a positive integer, received: '{type(ftp).__name__}'"
                )

    def visit_segment_block(self, params: PARAM_T, block_tag: Tag) -> None:
        required_tags = {Tag.DURATION}
        if block_tag == Tag.SEGMENT:
            required_tags = required_tags | {Tag.POWER}

        _check_keys(required_tags, params.keys(), block_tag)

    def visit_ramp_block(self, params: PARAM_T, block_tag: Tag) -> None:
        required_tags = {Tag.DURATION, Tag.POWER}
        _check_keys(required_tags, params.keys(), block_tag)

    def visit_interval_block(self, params: PARAM_T, block_tag: Tag) -> None:
        required_tags = {Tag.REPEAT, Tag.DURATION, Tag.POWER}
        _check_keys(required_tags, params.keys(), block_tag)

    def visit_power(self, power_spec: VAL_T) -> None:
        # Validate that an FTP is set in order to use absolute watts
        if isinstance(power_spec, int):
            if power_spec == 0:  # The parser already won't accept negative numbers
                raise ZWOMValidationError(f"Power must be > 0, received: {power_spec}")

            if not self._ftp:
                raise ZWOMValidationError(
                    "An FTP must be specified in the META block to use absolute watts."
                )
        elif isinstance(power_spec, Range):
            if not self._ftp:
                if isinstance(power_spec.left, int) or isinstance(power_spec.right, int):
                    raise ZWOMValidationError(
                        "An FTP must be specified in the META block to use absolute watts."
                    )

    def visit_cadence(self, cadence_spec: VAL_T, block_tag: Tag) -> None:
        # Cadence range is only valid for use in an interval block
        if isinstance(cadence_spec, Range) and block_tag != Tag.INTERVALS:
            raise ZWOMValidationError("Cadence ranges are only valid for Interval blocks.")

        if block_tag == Tag.INTERVALS and not isinstance(cadence_spec, Range):
            raise ZWOMValidationError("Cadence spec for Interval blocks must be a range.")
