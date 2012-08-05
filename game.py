import json
import itertools

from room import Room

class Game(object):
    def __init__(self):
        self.refresh_from_files()
    
    def update_shared_walls(self):
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
