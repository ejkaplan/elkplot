# The `elk` CLI

ElkPlot comes with a CLI that you can use in any environment in which the package is installed. The cli command is `elk`, and you can use the following commands to directly control the AxiDraw. The usage is fairly self-explanatory,
but a good starting point is calling `elk --help`


```commandline
> elk --help
Usage: elk [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  down  Bring the pen down onto the page
  goto  Move the pen directly to the point (x, y)
  home  Return the pen to (0, 0)
  move  Offset the pen's current position.
  off   Disable the AxiDraw's motors
  on    Enable the AxiDraw's motors
  up    Lift the pen off the page
  zero  Set the current location as (0, 0)

```

Note that for the `elk move` command, you need to use a double hyphen to indicate moving in the negative direction. For example, `elk move 2 --3` will move the pen 2 inches to the right and 3 inches up.