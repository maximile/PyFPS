import math
import inputstates
import pymunk
import utils
from utils import PLAYER_COLLISION_TYPE

# Movement properties
WALK_SPEED = 3.0
RUN_SPEED = 6.0

# Height properties
HEIGHT = 1.75
EYE_HEIGHT = 1.6
CROUCH_HEIGHT = 0.6
EYE_LIMIT = 0.2  # Minimum distance from the eye to the floor or ceiling

# Physics simulation properties
MASS = 10.0
FRICTION = 0.0
RADIUS = 0.4

def on_player_hit_wall(space, arbiter):
    player_shape, wall_shape = arbiter.shapes
    player = player_shape.player
    room = wall_shape.room
    wall_index = wall_shape.wall_index
    if wall_index in room.shared_walls:
        return False
    return True

class Player(object):
    def __init__(self, data):
        self.game = None
        self._current_room = None
        
        # Physical representation
        self.body = None
        self.radius = RADIUS

        # Position in space
        self.position = tuple(data["position"])
        self.heading = data.get("heading", 0.0)
        self.pitch = data.get("pitch", 0.0)
        self.z_pos = 0.0
        self.z_speed = 0.0
        self.tallness = self.z_pos + HEIGHT
        
        # Keep track of input (use constants - FORWARDS etc.)
        self.input_states = set()
        # Player has to press space once for each jump
        self.already_jumped = False
    
    @property
    def position(self):
        if self.body:
            return self.body.position
        else:
            return self._position
    
    @position.setter
    def position(self, new_position):
        if self.body:
            self.body.position = new_position
        else:
            self._position = new_position
    
    @property
    def grounded(self):
        """Whether the player is standing on the floor.
        
        """
        if not self.current_room:
            return False
        if self.z_pos <= self.current_room.floor_height:
            return True
        return False
    
    @property
    def eye_height(self):
        """Z position of the player's eyes.
        
        """
        # Add the current head height to the 
        return self.tallness - (HEIGHT - EYE_HEIGHT) + self.z_pos
    
    @property
    def current_room(self):
        """The current room that the player is in. Pass a list of all rooms
        you want to test against.
        
        """
        return self._current_room
        
    def get_current_room(self):
        distant_point = (0.0, 1e10)
        player_to_distance = (tuple(self.position), distant_point)
        for room in self.game.rooms:
            # Count the times it crosses the room's boundary. Odd = inside.
            cross_count = 0
            for wall in room.walls:
                if utils.lines_intersect(player_to_distance, wall):
                    cross_count += 1
            if cross_count % 2 == 1:
                return room
        
        # Inside no room
        return None
        
    def add_to_space(self, space):
        self.dragger = pymunk.Body(MASS, pymunk.inf)
        self.dragger.position = self._position
        space.add(self.dragger)

        self.body = pymunk.Body(MASS, pymunk.inf)
        self.body.position = self._position
        space.add(self.body)
        
        self.shape = pymunk.Circle(self.body, self.radius)
        self.shape.friction = FRICTION
        self.shape.collision_type = PLAYER_COLLISION_TYPE
        self.shape.player = self
        space.add(self.shape)
        
        constraint = pymunk.PinJoint(self.body, self.dragger)
        space.add(constraint)
    
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
    
    def jump(self):
        """Jump if possible. Return whether it was possible.
        
        """
        if self.grounded:
            self.z_speed += 0.5
            return True
        return False
    
    def update(self, dt):
        """Update the player position based on the keyboard input.
        
        """
        # Cache the current room
        self._current_room = self.get_current_room()

        # Outside the level? Can't do anything useful.
        if not self.current_room:
            return

        # Speed depends on 'run' input
        if inputstates.RUN in self.input_states:
            speed = RUN_SPEED
        else:
            speed = WALK_SPEED
        
        
        # Jump if the space key is down, but only if the player has released
        # it since the last jump.
        if inputstates.JUMP in self.input_states and not self.already_jumped:
            self.should_jump = True
            # Try to jump, and find out whether it succeeded
            jump_result =  self.jump()
            if jump_result:
                self.already_jumped = True
        if not inputstates.JUMP in self.input_states:
            self.already_jumped = False
        
        # If we're crouching, move the head height towards the crouch height.
        # Otherwise move the head height towards the regular height.
        # (Remember we're not taking the actual z position of the player here,
        # just the distance from head to feet.)
        must_crouch = False
        if (self.current_room.ceiling_height -
            self.current_room.floor_height < HEIGHT):
            must_crouch = True
        if inputstates.CROUCH in self.input_states or must_crouch:
            target_height = CROUCH_HEIGHT
        else:
            target_height = HEIGHT
        self.tallness = (self.tallness + target_height) / 2.0
        
        # Update the player's z position. First move them towards the floor if
        # their feet are below it.
        if self.z_pos < self.current_room.floor_height:
            self.z_pos = (self.z_pos + self.current_room.floor_height) / 2
    
        # If they're in the air, they should feel the effect of gravity
        if self.z_pos > self.current_room.floor_height:
            self.z_speed -= 0.05
        # On the ground? Stop falling
        if self.z_speed < 0.0 and self.z_pos < self.current_room.floor_height:
            self.z_speed = 0.0
        # Hit the ceiling? Start falling
        if self.z_pos + self.tallness >= self.current_room.ceiling_height:
            if self.z_speed > 0.0:
                self.z_speed = 0.0
            # Move the head out of the ceiling
            target_z_pos = self.current_room.ceiling_height - self.tallness
            self.z_pos = (self.z_pos + target_z_pos) / 2.0
        
        # And integrate the Z speed
        self.z_pos += self.z_speed
        
        # Finally, if the eye is too close to the floor or celing we clamp it
        eye_height = self.z_pos + self.tallness
        if eye_height < self.current_room.floor_height + EYE_LIMIT:
            target_eye_height = self.current_room.floor_height + EYE_LIMIT
            self.z_speed = 0.0
        if eye_height > self.current_room.ceiling_height - EYE_LIMIT:
            target_eye_height = self.current_room.ceiling_height - EYE_LIMIT
            self.z_speed = 0.0
        else:
            target_eye_height = eye_height
        self.z_pos += target_eye_height - eye_height
        
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
        if self.body:
         	self.dragger.velocity = (offset_x, offset_y)
         	self.dragger.position = (self.body.position.x + offset_x * dt,
         	                      self.body.position.y + offset_y * dt)
        else:
            self.position = (self.position[0] + offset_x * dt,
                             self.position[1] + offset_y * dt)
        
        # Set the view height based on the current room
        
        

    def on_mouse_moved(self, dx, dy):
        self.heading -= dx / 100.0
        self.pitch += dy / 100.0
        if self.pitch< -math.pi / 2:
            self.pitch = -math.pi / 2
        if self.pitch > math.pi / 2:
            self.pitch = math.pi / 2
        