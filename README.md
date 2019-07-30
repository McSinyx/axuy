# axuy

Mininalist first-person shooter

![icon](axuy/icon.png)

## Installation

The game is still under development. For testing, first install GLFW version 3.3
(or higher), then install the game in editable mode:

```sh
$ git clone https://github.com/McSinyx/axuy.git
$ pip3 install --user --editable axuy
$ axuy
Axuy is listening at 127.0.0.1:42069
```

Currently, the p2p connection is still buggy but at least it works I guess.
In another terminal, execute `axuy --seeder=127.0.0.1:42069`.
The two Picos might be spawn far away from each other but definitely
they exist with the same map.
