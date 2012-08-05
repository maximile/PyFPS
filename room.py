import math
import itertools

class InvalidRoomError(Exception):
    """Raised when the room data isn't valid.
    
    """
    pass

class Room(object):
    def __init__(self, data):
        # Wall vertex data, ordered clockwise
        self.vertices = []
        for vertex in data["vertices"]:
            self.vertices.append(tuple(vertex))
        # Correct incorrect winding
        try:
            self.check_winding()
        except InvalidRoomError:
            self.vertices.reverse()
        # Check for other errors
        self.check_walls()
        
        # Walls shared with other rooms; key = wall index, value = other room
        self.shared_walls = {}
    
    @property
    def walls(self):
        """List of walls from the room's vertex data.
        
        >>> a = 0.0, 0.0  # c
        >>> b = 1.0, 0.0  # 
        >>> c = 0.0, 1.0  # a    b
        >>> Room((a, b, c)).walls == [(a, b), (b, c), (c, a)]
        True
        
        """
        walls = []
        for i, vertex_a in enumerate(self.vertices):
            try:
                vertex_b = self.vertices[i + 1]
            except IndexError:  # Loop back to the start
                vertex_b = self.vertices[0]
            walls.append((vertex_a, vertex_b))
        return walls
    
    def check_winding(self):
        """Raises InvalidRoomError if the vertices aren't wound clockwise.
        
        """
        # Add up the angles made by wall pairs
        total_angle = 0
        for i, wall_a in enumerate(self.walls):
            try:
                wall_b = self.walls[i + 1]
            except IndexError:
                wall_b = self.walls[0]
            
            for i, wall in enumerate([wall_a, wall_b]):
                vertex_a = wall[0]
                vertex_b = wall[1]
                offset_x = vertex_b[0] - vertex_a[0]
                offset_y = vertex_b[1] - vertex_a[1]
                angle = math.atan2(offset_y, offset_x)
                if i == 0:
                    angle_a = angle
                else:
                    angle_b = angle
            
            angle = (angle_b - angle_a)
            angle = math.fmod(angle, math.pi)
            total_angle += angle
        if total_angle > 0.0:
            raise InvalidRoomError("Rooms must be wound clockwise")
    
    
    def check_walls(self):
        """Make sure the vertices are valid.
        
        # >>> a = 0.0, 0.0  # c
        # >>> b = 1.0, 0.0  # 
        # >>> c = 0.0, 1.0  # a    b
        # >>> Room((a, b, c)).check_walls()
        
        Checks for self-intersection and winding.
        
        """
        # Make sure every vertex is unique
        if not len(set(self.vertices)) == len(self.vertices):
            raise InvalidRoomError("Vertices aren't unique.")
        
        # Check for intersection. Loop over every pair of walls:
        for wall_a, wall_b in itertools.combinations(self.walls, 2):
            if lines_intersect(wall_a, wall_b):
                raise InvalidRoomError("Walls intersect: %s, %s" %
                                       (wall_a, wall_b))
        
        # Check winding:
        self.check_winding()
        


def lines_intersect(line_one, line_two):
    """Whether the two lines cross each other.
    
    >>> point_a = (-1.0, 0.0)  #   b
    >>> point_b = (0.0, 1.0)   # a + c
    >>> point_c = (1.0, 0.0)   #   d
    >>> point_d = (0.0, -1.0)  #
    >>> lines_intersect((point_a, point_b), (point_c, point_d))
    False
    >>> lines_intersect((point_a, point_c), (point_b, point_d))
    True
    
    Each line is a tuple of two points, each points is a tuple of two 
    coordinates.
    
    """
    # First check for shared vertices
    unique_points = set([line_one[0], line_one[1], line_two[0], line_two[1]])
    if len(unique_points) == 1:
        raise ValueError("Invalid lines")
    elif len(unique_points) == 2:
        raise ValueError("The lines are the same")
    elif len(unique_points) == 3:
        # One shared vertex; the lines join at one end so they can't intersect
        return False
    
    ax = line_one[0][0]
    ay = line_one[0][1]
    bx = line_one[1][0]
    by = line_one[1][1]
    cx = line_two[0][0]
    cy = line_two[0][1]
    dx = line_two[1][0]
    dy = line_two[1][1]
    
    # Magic (http://www.faqs.org/faqs/graphics/algorithms-faq/ 1.03)
    try:
        r = (((ay - cy) * (dx - cx) - (ax - cx) * (dy - cy)) /
            ((bx - ax) * (dy - cy) - (by - ay) * (dx - cx)))
    except ZeroDivisionError:
        # Lines are parallel
        return False
    s = (((ay - cy) * (bx - ax) - (ax - cx) * (by - ay)) / 
         ((bx - ax) * (dy - cy) - (by - ay) * (dx - cx)))
    
    if 0.0 <= r <= 1.0 and 0.0 <= s <= 1.0:
        return True
    else:
        return False

