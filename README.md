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

## Installation

The game is still work-in-progress. For testing, first install GLFW version 3.3
(or higher), then install the game in editable mode:

```sh
$ git clone https://github.com/McSinyx/axuy.git
$ pip3 install --user --editable axuy
$ axuy --port=42069 &
$ axuy --seeder=:42069
```

There is also `aisample` in `tools` as an automated example
with similar command-line interface.
