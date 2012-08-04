from room import Room

class Game(object):
    def __init__(self):
        rooms = []
        room_one = Room()
        room_one.vertices = [(3.0, 3.0),
                             (8.0, 3.0),
                             (8.0, 6.0),
                             (7.0, 6.0),
                             (7.0, 7.0),
                             (4.0, 7.0),
                             (4.0, 6.0),
                             (3.0, 6.0)]
        room_two = Room()
        room_two.vertices = [(4.0, 7.0),
                             (7.0, 7.0),
                             (7.0, 9.0),
                             (12.0, 9.0),
                             (12.0, 12.0),
                             (4.0, 12.0)]
        # room_three = Room()
        # room_three.vertices = [(3.0, 3.0), (8.0, 3.0), (8.0, 6.0), (3.0, 6.0)]
        
        self.rooms = [room_one, room_two]