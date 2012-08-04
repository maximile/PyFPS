#!/usr/bin/env python
import pyglet
import window
import game

def main():
    the_game = game.Game()
    window.set_game(the_game)
    pyglet.app.run()

if __name__ == "__main__":
    main()
