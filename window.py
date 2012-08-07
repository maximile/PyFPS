import pyglet.window
from pyglet.window import key

class Window(pyglet.window.Window):
    def __init__(self, view, *args, **kwargs):
        pyglet.window.Window.__init__(self, *args, **kwargs)
        self.view = view
        self.view.size = (self.width, self.height)

    def on_activate(self):
        self.view.game.refresh_from_files()
        self.set_exclusive_mouse(True)
    
    def on_deactivate(self):
        self.set_exclusive_mouse(False)
    
    def on_mouse_motion(self, x, y, dx, dy):
        self.view.game.player.on_mouse_moved(dx, dy)
    
    def on_key_press(self, symbol, modifiers):
        if symbol == key.A:
            self.view.a_down = True
        elif symbol == key.S:
            self.view.s_down = True
        elif symbol == key.W:
            self.view.w_down = True
        elif symbol == key.D:
            self.view.d_down = True
        elif symbol == key._1:
            self.view.draw_func = self.view.draw_2d
        elif symbol == key._3:
            self.view.draw_func = self.view.draw_3d
        else:
            return
        self.view.update_player_movement_from_keys()
        
    def on_key_release(self, symbol, modifiers):
        if symbol == key.A:
            self.view.a_down = False
        elif symbol == key.S:
            self.view.s_down = False
        elif symbol == key.W:
            self.view.w_down = False
        elif symbol == key.D:
            self.view.d_down = False
        else:
            return
        self.view.update_player_movement_from_keys()
    
    def on_draw(self):        
        self.view.draw()
