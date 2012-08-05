import math

class Player(object):
    def __init__(self, data):
        self.position = tuple(data["position"])
        self.heading = data.get("heading", 0.0)
        self.pitch = data.get("pitch", 0.0)
        self.movement = 0.0, 0.0
        
    def update(self, dt):
        offset_x = (math.cos(self.heading) * self.movement[0] -
                    math.sin(self.heading) * self.movement[1])
        offset_y = (math.sin(self.heading) * self.movement[0] +
                    math.cos(self.heading) * self.movement[1])
        self.position = (self.position[0] + offset_x * dt,
                         self.position[1] + offset_y * dt)

    def on_mouse_moved(self, dx, dy):
        self.heading -= dx / 100.0
        self.pitch += dy / 100.0
    	if self.pitch< -math.pi / 2:
    	    self.pitch = -math.pi / 2
    	if self.pitch > math.pi / 2:
    	    self.pitch = math.pi / 2
    	