import pyglet
from pyglet.gl import *

_window = pyglet.window.Window()

class View(object):
    def __init__(self, game):
        self.game = game
    
    def draw(self):
        glColor4f(0.0, 0.0, 0.0, 1.0)
        for room in self.game.rooms:
            glBegin(GL_LINE_LOOP)
            for vertex in room.vertices:
                glVertex2f(vertex[0], vertex[1])
            glEnd()

view = None
def set_game(game):
    global view
    view = View(game)


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
