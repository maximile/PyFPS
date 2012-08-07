import json
import itertools

from room import Room
from player import Player
import pymunk

class Game(object):
    def __init__(self):
        self.refresh_from_files()
        
    def update_shared_walls(self):
        if len(self.rooms) <2:
            return
        shared_walls = []
        # Loop over every pair of rooms
        for room_a, room_b in itertools.combinations(self.rooms, 2):
            for index_a, wall_a in enumerate(room_a.walls):
                for index_b, wall_b in enumerate(room_b.walls):
                    # We know they're both wound the same way, so the walls 
                    # will be in opposite directions
                    if wall_a[0] == wall_b[1] and wall_a[1] == wall_b[0]:
                        # The walls are shared; record the shared rooms
                        room_a.shared_walls[index_a] = room_b
                        room_b.shared_walls[index_b] = room_a

    def refresh_from_files(self):
        data = json.load(open("level.json", "r"))
        self.rooms = []
        for room_data in data["rooms"]:
            self.rooms.append(Room(room_data))
        self.update_shared_walls()
        for room in self.rooms:
            room.generate_triangulated_data()
        
        self.player = Player(data["player"])
        
        # Setup physics objects
        self.space = pymunk.Space()
        self.space.damping = 0.5
    	self.space.gravity = (0.0, -100.0)
    	
    	# Let each object add themselves
    	for room in self.rooms:
    	    room.add_to_space(self.space)
	    self.player.add_to_space(self.space)
        

    def update(self, dt):
        self.player.update(dt)
        self.space.step(dt)
