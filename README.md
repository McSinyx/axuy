# axuy

Mininalist peer-to-peer first-person shooter

![icon](https://raw.githubusercontent.com/McSinyx/axuy/master/axuy/icon.png)

## Goals

* Written in pure Python and thus be portable
* Easy to read codebase as well as easy on resources
* Generative visuals
* Functional when possible
* P2P communication based on calculated *trust*
* Modularized for the ease of bot scripting

## Screenshots

Since axuy's screenshots would look like some kinky abstract art,
I instead document the development progress as short clips on Youtube,
[listed in reverse chronological order][yt].  If software freedom is concerned,
one may view them using MPV with youtube-dl support.

## Installation

The game is still work-in-progress.  Preview releases are available on PyPI
and can be installed for Python 3.6+ via

    pip install axuy

Unless one is on either Windows or macOS, perse would have to
additionally install GLFW version 3.3 (or higher).

Axuy can then be launch from the command-line using

    axuy --port=42069 &
    axuy --seeder=:42069

There is also `aisample` in `tools` as an automated example
with similar command-line interface.

For hacking, after having dependenies installed, one may also invoke axuy
from the project's root directory by

    python -m axuy --port=42069 &
    python -m axuy --seeder=:42069

[yt]: https://www.youtube.com/playlist?list=PLAA9fHINq3sayfxEyZSF2D_rMgDZGyL3N
