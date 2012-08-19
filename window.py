import pyglet.window
from pyglet.window import key

from view import VIEW_2D, VIEW_3D, VIEW_INCIDENT

import inputstates

class Window(pyglet.window.Window):
    def __init__(self, view, *args, **kwargs):
        pyglet.window.Window.__init__(self, *args, **kwargs)
        self.view = view
        self.view.size = (self.width, self.height)

    def on_activate(self):
        # self.view.game.refresh_from_files()
        self.set_exclusive_mouse(True)
    
    def on_deactivate(self):
        self.set_exclusive_mouse(False)
    
    def on_mouse_motion(self, x, y, dx, dy):
        self.view.game.player.on_mouse_moved(dx, dy)
    
    def on_key_press(self, symbol, modifiers):
        if symbol == key.A:
            self.view.game.player.input_changed(inputstates.LEFT, True)
        elif symbol == key.S:
            self.view.game.player.input_changed(inputstates.BACKWARDS, True)
        elif symbol == key.W:
            self.view.game.player.input_changed(inputstates.FORWARDS, True)
        elif symbol == key.D:
            self.view.game.player.input_changed(inputstates.RIGHT, True)
        elif symbol == key.LSHIFT:
            self.view.game.player.input_changed(inputstates.RUN, True)
        elif symbol == key.LCTRL:
            self.view.game.player.input_changed(inputstates.CROUCH, True)
        elif symbol == key.SPACE:
            self.view.game.player.input_changed(inputstates.JUMP, True)
        elif symbol == key._1:
            self.view.view_mode = VIEW_2D
        elif symbol == key._3:
            self.view.view_mode = VIEW_3D
        elif symbol == key._4:
            self.view.view_mode = VIEW_INCIDENT
        else:
            return
        self.view.update_player_movement_from_keys()
        
    def on_key_release(self, symbol, modifiers):
        if symbol == key.A:
            self.view.game.player.input_changed(inputstates.LEFT, False)
        elif symbol == key.S:
            self.view.game.player.input_changed(inputstates.BACKWARDS, False)
        elif symbol == key.W:
            self.view.game.player.input_changed(inputstates.FORWARDS, False)
        elif symbol == key.D:
            self.view.game.player.input_changed(inputstates.RIGHT, False)
        elif symbol == key.LSHIFT:
            self.view.game.player.input_changed(inputstates.RUN, False)
        elif symbol == key.LCTRL:
            self.view.game.player.input_changed(inputstates.CROUCH, False)
        elif symbol == key.SPACE:
            self.view.game.player.input_changed(inputstates.JUMP, False)
        else:
            return
        self.view.update_player_movement_from_keys()
    
    def on_draw(self):        
        self.view.draw()
