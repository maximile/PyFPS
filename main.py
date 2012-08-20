#!/usr/bin/env python
import os
import pyglet
from game import Game
from view import View
from window import Window

def main():
    # Resources should be loaded relative to the resources dir
    resources_dir = os.path.join(os.path.dirname(__file__), "resources")
    os.chdir(resources_dir)
    game = Game()
    view = View(game)
    window = Window(view=view, width=800, height=500)
    pyglet.clock.schedule_interval(game.update, 1.0 / 60.0)
    
    import radiosity
    map = radiosity.get_shape_compensation_map()
    map.save("/tmp/map.png")
    
    pyglet.app.run()

if __name__ == "__main__":
    main()
