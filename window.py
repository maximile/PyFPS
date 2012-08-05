import pyglet
from pyglet.gl import *

_window = pyglet.window.Window()

SHARED_WALL_COLOR = 0.7, 0.7, 0.7, 1.0
WALL_COLOR = 0.0, 0.0, 0.0, 1.0

class View(object):
    def __init__(self, game):
        self.game = game
    
    def draw(self):
        for room in self.game.rooms:
            for i, wall in enumerate(room.walls):
                if i in room.shared_walls:
                    glColor4f(*SHARED_WALL_COLOR)
                else:
                    glColor4f(*WALL_COLOR)
                glBegin(GL_LINES)
                for vertex in wall:
                    glVertex2f(vertex[0], vertex[1])
                glEnd()

view = None
def set_game(game):
    global view
    view = View(game)


@_window.event
def on_activate():
    view.game.refresh_from_files()

@_window.event
def on_draw():
    glLoadIdentity()
    
    glClearColor(1.0, 1.0, 1.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    scale = 10.0
    glViewport(0, 0, _window.width, _window.height)
    glOrtho(0.0, 0.1, 0.0, 0.1, -1.0, 1.0)
    # glOrtho(0.0, _window.width, 0.0, _window.height, -1.0, 1.0)
    # glOrtho(0, _window.width / scale, 0, _window.height / scale, -10.0, 10.0)
    view.draw()
