# ZWO Minilang
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zwolang/0.3.0?logo=python&logoColor=FFD43B)](https://pypi.org/project/zwolang/)
[![PyPI](https://img.shields.io/pypi/v/zwolang)](https://pypi.org/project/zwolang/)
[![PyPI - License](https://img.shields.io/pypi/l/zwolang?color=magenta)](https://github.com/sco1/zwom/blob/master/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/zwom/main.svg)](https://results.pre-commit.ci/latest/github/sco1/zwom/main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Open in Visual Studio Code](https://img.shields.io/badge/Open%20in-VSCode.dev-blue)](https://vscode.dev/github.com/sco1/zwom)

Python toolkit for the ZWO minilang.

## Installation
Install from PyPi with your favorite `pip` invocation:

```bash
$ pip install zwolang
```

You can confirm proper installation via the `zwom` CLI:
<!-- [[[cog
import cog
from subprocess import PIPE, run
out = run(["zwom", "--help"], stdout=PIPE, encoding="ascii")
cog.out(
    f"```\n$ zwom --help\n{out.stdout.rstrip()}\n```"
)
]]] -->
```
$ zwom --help

 Usage: zwom [OPTIONS] COMMAND [ARGS]...

+- Options -------------------------------------------------------------------+
| --help          Show this message and exit.                                 |
+-----------------------------------------------------------------------------+
+- Commands ------------------------------------------------------------------+
| batch    Discover and convert all `*.zwom` files in the given directory.    |
| single   Convert the specified `*.zwom` file to Zwift's `*.zwo`.            |
+-----------------------------------------------------------------------------+
```
<!-- [[[end]]] -->

## The ZWOM File Specification
The primary purpose of this package is to provide a simple, human-readable format for constructing Zwift workouts that can be used to generate the actual workout XML. Let's call it a `*.zwom` file, or ZWOM.

ZWOM files are parsed using a [Parsimonious](https://github.com/erikrose/parsimonious) grammar, as specified below:
<!-- [[[cog
from textwrap import dedent
import cog
from zwo.parser import RAW_GRAMMAR
cog.out(
    f"```{dedent(RAW_GRAMMAR)}```"
)
]]] -->
```
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
```
<!-- [[[end]]] -->

### Syntax & Keywords
Like Zwift's built-in workout builder, the ZWO minilang is a block-based system. Blocks are specified using a `<tag> {<block contents>}` format supporting arbitrary whitespace.

Inline comments are also supported, denoted by a leading `;`.

### Workout Metadata
Each ZWO file must begin with a `META` block containing comma-separated parameters:

| Keyword       | Description             | Accepted Inputs                | Optional?         |
|---------------|-------------------------|--------------------------------|-------------------|
| `NAME`        | Displayed workout name  | `str`                          | No                |
| `AUTHOR`      | Workout author          | `str`                          | No                |
| `DESCRIPTION` | Workout description     | `str`<sup>1</sup>              | No                |
| `FTP`         | Rider's FTP             | `int`                          | Maybe<sup>2</sup> |
| `TAGS`        | Workout tags            | String of hashtags<sup>3</sup> | Yes               |

1. Multiline strings are supported
2. Zwift's workouts are generated using FTP percentages rather than absolute watts, so your FTP is required if you want to use absolute watts in your ZWOM
3. Tags are capped at 31 total characters, including spaces and hashtags. Zwift also provides 4 built-in tags (`#RECOVERY`, `#INTERVALS`, `#FTP`, and `#TT`) that may also be added and do not count against this total.

### Workout Blocks
Following the `META` block are your workout blocks:

| Keyword     | Description        |
|-------------|--------------------|
| `FREE`      | Free ride          |
| `COOLDOWN`  | Cooldown           |
| `INTERVALS` | Intervals          |
| `RAMP`      | Ramp               |
| `SEGMENT`   | Steady segment     |
| `WARMUP`    | Warmup             |

**NOTE:** While there is no specific Ramp block in the workout building UI, some experimental observations have been made:
  * If a Ramp is at the very beginning of the workout, Zwift serializes it as a Warmup block
  * If there are multiple blocks in a workout and a Ramp is at the end, there are two paths:
    * If the left power is higher than the right power, Zwift serializes it as a Cooldown block
    * If the right power is higher than the left power, Zwift serializes it as a Ramp block
  * If there are multiple blocks in a workout and a Ramp is not at the beginning nor the end, Zwift serializes it as a Ramp block

When writing your `*.zwom` file, these 3 blocks can be used interchangably, and ZWOM will try to match this behavior when outputting its `*.zwo` file. Zwift may do its own normalization if edits are made in the workout UI.

### Workout Block Metadata
Workout blocks can contain the following (optionally) comma-separated parameters:

| Keyword    | Description         | Accepted Inputs                                    | Optional?                |
|------------|---------------------|----------------------------------------------------|--------------------------|
| `DURATION` | Block duration      | `MM:SS`, Range<sup>1</sup>                         | No                       |
| `CADENCE`  | Target cadence      | `int`, Range<sup>1,2</sup>                         | Yes                      |
| `REPEAT`   | Number of intervals | `int`                                              | Only valid for intervals |
| `POWER`    | Target power        | `int`, `int%`, Zone<sup>3</sup>, Range<sup>1</sup> | Mostly no<sup>4</sup>    |
| `@`        | Display a message   | `@ MM:SS str`<sup>5</sup>                          | Yes                      |

1. For Interval & Ramp segments, the range syntax can be used to set values for the `<left> -> <right>` segments (e.g. `65% -> 120%` or `Z2 -> Z6`)
2. Cadence ranges are only valid for Interval segments
3. Zones may be specified as `Z1-7` or `SS`
4. Power is ignored for Free segments
5. Message timestamps are relative to their containing block

### Repeating a Chunk of Blocks
The `START_REPEAT` and `END_REPEAT` meta blocks are provided to specify an arbitrary chunk of blocks to repeat. The `START_REPEAT` block must specify a `REPEAT` parameter; `END_REPEAT` accepts no parameters. Nested repeats are not currently supported.

For example:

```
SEGMENT {DURATION 2:00, POWER 65%}
RAMP {
    DURATION 2:00,
    POWER 120% -> 140%,
    @ 0:00 "Here goes the ramp!",
    @ 1:50 "10 seconds left!",
}
SEGMENT {DURATION 2:00, POWER 65%}
RAMP {
    DURATION 2:00,
    POWER 120% -> 140%,
    @ 0:00 "Here goes the ramp!",
    @ 1:50 "10 seconds left!",
}
```
Becomes:

```
START_REPEAT {REPEAT 2}
SEGMENT {DURATION 2:00, POWER 65%}
RAMP {
    DURATION 2:00,
    POWER 120% -> 140%,
    @ 0:00 "Here goes the ramp!",
    @ 1:50 "10 seconds left!",
}
END_REPEAT {}
```

## Sample Workout
```
; Here is a workout-level comment!
META {
    NAME "Sample Workout",
    AUTHOR "sco1",
    DESCRIPTION "Here's a description!

    Descriptions may be on more than one line too!",
    TAGS "#RECOVERY #super #sweet #workout",
    FTP 270,
}
FREE {DURATION 10:00}
INTERVALS {
    ; Here is a block-level comment!
    REPEAT 3,
    DURATION 1:00 -> 0:30,
    POWER 55% -> 78%,
    CADENCE 85 -> 110,
}
SEGMENT {DURATION 2:00, POWER 65%}
RAMP {
    DURATION 2:00,
    POWER 120% -> 140%,
    @ 0:00 "Here goes the ramp!",
    @ 1:50 "10 seconds left!",
}
FREE {DURATION 10:00}
```

![Workout Screenshot](https://raw.githubusercontent.com/sco1/sco1.github.io/master/zwo/sample_zwift_workout.png)
