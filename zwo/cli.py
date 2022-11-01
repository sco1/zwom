from pathlib import Path

import click
import typer
from sco1_misc import prompts

from zwo.serialize import convert_zwom

zwom_cli = typer.Typer(add_completion=False, no_args_is_help=True)


@zwom_cli.command()
def single(
    zwom_file: Path = typer.Option(None, exists=True, dir_okay=False),
    out_file: Path = typer.Option(None),
) -> None:
    """
    Convert the specified `*.zwom` file to Zwift's `*.zwo`.

    `out_file` may be optionally specified, otherwise the file will be output to the same directory
    with the file extension swapped.

    NOTE: Any existing `*.zwo` file with the same name will be overwritten.
    """
    if zwom_file is None:
        try:
            zwom_file = prompts.prompt_for_file(
                title="Select ZWOM file for conversion", filetypes=[("ZWOM", "*.zwom")]
            )
        except ValueError:
            raise click.ClickException("No file selected, aborting.")

    convert_zwom(zwom_file, out_file)


@zwom_cli.command()
def batch(
    top_dir: Path = typer.Option(None, exists=True, dir_okay=True),
    recursive: bool = typer.Option(False),
) -> None:
    """
    Discover and convert all `*.zwom` files in the given directory.

    NOTE: Any existing `*.zwo` file with the same name will be overwritten.
    """
    if top_dir is None:
        try:
            top_dir = prompts.prompt_for_dir(title="Select ZWOM directory")
        except ValueError:
            raise click.ClickException("No directory selected, aborting.")

    pattern = "*.zwom"
    if recursive:
        pattern = f"**/{pattern}"

    for file in top_dir.glob(pattern):
        convert_zwom(file)


if __name__ == "__main__":  # pragma: no cover
    zwom_cli()
