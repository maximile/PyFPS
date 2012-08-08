#!/usr/bin/env python
import pyglet
from game import Game
from view import View
from window import Window

def main():
    game = Game()
    view = View(game)
    window = Window(view=view, width=800, height=500)
    pyglet.clock.schedule_interval(game.update, 1.0 / 60.0)
    pyglet.app.run()

if __name__ == "__main__":
    main()
