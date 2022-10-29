# ZWO Minilang
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/zwolang)](https://pypi.org/project/zwolang/)
[![PyPI](https://img.shields.io/pypi/v/zwolang)](https://pypi.org/project/zwolang/)
[![PyPI - License](https://img.shields.io/pypi/l/zwolang?color=magenta)](https://github.com/sco1/zwolang/blob/master/LICENSE)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/sco1/zwolang/main.svg)](https://results.pre-commit.ci/latest/github/sco1/zwolang/main)
[![Code style: black](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Open in Visual Studio Code](https://img.shields.io/badge/Open%20in-VSCode.dev-blue)](https://vscode.dev/github.com/sco1/zwolang)

Python toolkit for the ZWO minilang.

## Installation
Install from PyPi with your favorite `pip` invocation:

```bash
$ pip install zwolang
```

## The ZWO File Specification
The primary purpose of this package is to provide a simple, human-readable format for constructing Zwift workouts that can be used to generate the actual workout XML. Let's call it a `*.zwom` file, or ZWOM.

ZWO files are parsed using a [Parsimonious](https://github.com/erikrose/parsimonious) grammar, as specified below:
<!-- [[[cog
from textwrap import dedent
import cog
from zwo.parser import RAW_GRAMMAR
cog.out(
    f"```{dedent(RAW_GRAMMAR)}```"
)
]]] -->
```
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
```
<!-- [[[end]]] -->

### Syntax & Keywords
Like Zwift's built-in workout builder, the ZWO minilang is a block-based system. Blocks are specified using a `<tag> {<block contents>}` format supporting arbitrary whitespace.

### Workout Metadata
Each ZWO file must begin with a `META` block containing comma-separated parameters:

| Keyword       | Description             | Accepted Inputs                | Optional?         |
|---------------|-------------------------|--------------------------------|-------------------|
| `NAME`        | Displayed workout name  | `str`                          | No                |
| `AUTHOR`      | Workout author          | `str`                          | No                |
| `DESCRIPTION` | Workout description     | `str`<sup>1</sup>              | No                |
| `FTP`         | Rider's FTP             | `int`                          | Maybe<sup>2</sup> |
| `TAGS`        | Workout tags            | String of hashtags<sup>3</sup> | Yes               |

1. Multiline strings are supported.
2. Zwift's workouts are generated using FTP percentages rather than absolute watts, so your FTP is required if you want to use absolute watts in your ZWOM.
3. Tags are capped at x total characters, including hashtags. Zwift also provides 4 built-in tags (`#RECOVERY`, `#INTERVALS`, `#FTP`, and `#TT`) that may also be added and do not count against this total.

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
  * If a ramp is at the very beginning of the workout, Zwift serializes it as a Warmup block
  * If there are multiple blocks in a workout and a ramp is at the end, Zwift serializes it as a Cooldown block
  * If there are multiple blocks in a workout and a ramp is not at the beginning or the end, Zwift serializes it as a Ramp block

When writing your `*.zwom` file, these 3 blocks can be used interchangably, and ZWOM will try to match this behavior when outputting its `*.zwo` file. Zwift may do its own normalization if edits are made in the workout UI.

### Workout Block Metadata
Workout blocks can contain the following comma-separated parameters:

| Keyword    | Description         | Accepted Inputs             | Optional?                |
|------------|---------------------|-----------------------------|--------------------------|
| `DURATION` | Block duration      | `MM:SS`<sup>1</sup>         | No                       |
| `CADENCE`  | Target cadence      | `int`<sup>1</sup>           | Yes                      |
| `REPEAT`   | Number of intervals | `int`                       | Only valid for intervals |
| `POWER`    | Target power        | `int` or `int%`<sup>1</sup> | Mostly no<sup>2</sup>    |
| `@`        | Display a message   | `@ MM:SS str`<sup>3</sup>   | Yes                      |

1. For Interval & Ramp segments, the range syntax can be used to set values for the `<work> -> <rest>` segments (e.g. `65% -> 120%`).
2. Power is ignored for Free segments.
3. Message timestamps are relative to their containing block.


### Sample Workout
```
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
