import math
import inputstates

WALK_SPEED = 3.0
RUN_SPEED = 6.0

class Player(object):
    def __init__(self, data):
        self.position = tuple(data["position"])
        self.heading = data.get("heading", 0.0)
        self.pitch = data.get("pitch", 0.0)
        self.movement = 0.0, 0.0
        
        # Keep track of input (use constants - FORWARDS etc.)
        self.input_states = set()
    
    def input_changed(self, state, value):
        """Record the change in input on the player object.
        
        """
        if value:
            self.input_states.add(state)
        else:
            try:
                self.input_states.remove(state)
            except KeyError:
                pass
        
    def update(self, dt):
        """Update the player position based on the keyboard input.
        
        """
        # Speed depends on 'run' input
        if inputstates.RUN in self.input_states:
            speed = RUN_SPEED
        else:
            speed = WALK_SPEED
        
        # Calculate the player's velocity
        x_speed = 0
        y_speed = 0
        if inputstates.LEFT in self.input_states:
            y_speed += speed
        if inputstates.RIGHT in self.input_states:
            y_speed -= speed
        if inputstates.FORWARDS in self.input_states:
            x_speed += speed
        if inputstates.BACKWARDS in self.input_states:
            x_speed -= speed
        offset_x = (math.cos(self.heading) * x_speed -
                    math.sin(self.heading) * y_speed)
        offset_y = (math.sin(self.heading) * x_speed +
                    math.cos(self.heading) * y_speed)
        
        # Add the offset to the current position
        self.position = (self.position[0] + offset_x * dt,
                         self.position[1] + offset_y * dt)

    def on_mouse_moved(self, dx, dy):
        self.heading -= dx / 100.0
        self.pitch += dy / 100.0
    	if self.pitch< -math.pi / 2:
    	    self.pitch = -math.pi / 2
    	if self.pitch > math.pi / 2:
    	    self.pitch = math.pi / 2
    	