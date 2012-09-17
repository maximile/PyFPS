import json
import itertools

import pymunk

from radiosity import Radiosity
from room import Room
from player import Player, on_player_hit_wall

from utils import WALL_COLLISION_TYPE, PLAYER_COLLISION_TYPE

class Game(object):        
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
        data = json.load(open("levels/level.json", "r"))
        
        # Lightmaps that will have radiosity calculated, along with their 
        # sample camera function
        lightmaps = []
        
        # Add rooms from data
        self.rooms = []
        for room_data in data["rooms"]:
            self.rooms.append(Room(room_data))
        self.update_shared_walls()
        for room in self.rooms:
            room.generate_triangulated_data()
            lightmaps.extend(room.lightmaps)    
        
        self.player = Player(data["player"])
        self.player.game = self
        
        # Setup physics objects
        self.space = pymunk.Space()
        self.space.iterations = 100
    	
        # Let each object add themselves
        for room in self.rooms:
            room.add_to_space(self.space)
        self.player.add_to_space(self.space)
        
        # Add handler for collisions between player and walls
        self.space.add_collision_handler(PLAYER_COLLISION_TYPE,
                                         WALL_COLLISION_TYPE,
                                         pre_solve=on_player_hit_wall)
        
        # Object for managing radiosity
        self.radiosity = Radiosity(self.view.draw_for_lightmap, lightmaps)
        

    def update(self, dt):
        self.radiosity.do_work()
        self.player.update(1.0 / 60.0)
        for room in self.rooms:
            room.update(dt)
        self.space.step(1.0 / 60.0)
