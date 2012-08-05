#!/usr/bin/env python
import pyglet
import window
import game

def main():
    the_game = game.Game()
    window.set_game(the_game)
    pyglet.clock.schedule_interval(the_game.update, 1/60.0)
    pyglet.app.run()

if __name__ == "__main__":
    main()
