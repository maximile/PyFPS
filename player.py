import math
import inputstates
import pymunk

# Movement properties
WALK_SPEED = 3.0
RUN_SPEED = 6.0

# Physical properties
MASS = 10.0
FRICTION = 0.0
RADIUS = 0.4

class Player(object):
    def __init__(self, data):
        self.initial_position = tuple(data["position"])
        self.heading = data.get("heading", 0.0)
        self.pitch = data.get("pitch", 0.0)
        self.radius = RADIUS
        
        # Keep track of input (use constants - FORWARDS etc.)
        self.input_states = set()
    
    @property
    def position(self):
        return self.body.position
    
    def add_to_space(self, space):
    	self.dragger = pymunk.Body(MASS, pymunk.inf)
    	self.dragger.position = self.initial_position
    	space.add(self.dragger)

    	self.body = pymunk.Body(MASS, pymunk.inf)
    	self.body.position = self.initial_position
        print self.body.velocity
    	space.add(self.body)
        
        self.shape = pymunk.Circle(self.body, self.radius)
        self.shape.friction = FRICTION
        space.add(self.shape)
        
#        constraint = pymunk.PinJoint(self.body, self.dragger)
#        space.add(constraint)
    
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
        # self.position = (self.position[0] + offset_x * dt,
        #                  self.position[1] + offset_y * dt)

    def on_mouse_moved(self, dx, dy):
        self.heading -= dx / 100.0
        self.pitch += dy / 100.0
    	if self.pitch< -math.pi / 2:
    	    self.pitch = -math.pi / 2
    	if self.pitch > math.pi / 2:
    	    self.pitch = math.pi / 2
    	