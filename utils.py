import math
from pyglet.gl import *

# Unique collision type identifiers
PLAYER_COLLISION_TYPE = 1
WALL_COLLISION_TYPE = 2

def rad_to_deg(radians):
	return radians * 57.2957795

def deg_to_rad(degrees):
	return degrees / 57.2957795

def get_angle(vertex_before, vertex, vertex_after):
    """From three vertices defining two adjacent walls, find the angle between
    the walls.
    
    Results will be between -math.pi and math.pi. Negative values mean it's
    turning right.
    
    """
    wall_a = (vertex_before, vertex)
    wall_b = (vertex, vertex_after)
    
    # Get the angle of each wall
    angles = []
    for wall in wall_a, wall_b:
        vertex_a = wall[0]
        vertex_b = wall[1]
        offset_x = vertex_b[0] - vertex_a[0]
        offset_y = vertex_b[1] - vertex_a[1]
        angle = math.atan2(offset_y, offset_x)
        angles.append(angle)
    
    # Angle between the two, wrapped to (-math.pi, math.pi)  
    angle = (angles[1] - angles[0])
    if angle > math.pi:
        angle -= math.pi * 2
    if angle < -math.pi:
        angle += math.pi * 2
    return angle

def lerp(a, b, ratio):
    """Linearly interpolate between a and b using the given ratio (0.0 - 1.0)
    
    """
    return a + (b - a) * ratio

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

def get_length(point_a, point_b):
    """Distance between two 2D points.
    
    """
    x_offset = point_b[0] - point_a[0]
    y_offset = point_b[1] - point_a[1]
    return math.sqrt(x_offset * x_offset + y_offset * y_offset)

def is_power_of_two(value):
    """Whether the value is a power of two
    
    """
    int_val = int(value)
    if not int_val == value:
        raise ValueError("Not a whole number")
    if int_val < 2:
        return False
    
    # Magic
    if value & (value - 1) == 0:
        return True
    
    return False    

def triangulate(vertices):
    """List of triangles making up the given polygon.
    
    Vertices must be wound clockwise.
    
    """
    if not len(vertices) >= 3:
        raise ValueError("Not enough vertices")
    triangles = []
    # We're going to remove verts from this as they get added to triangles
    vertices = list(vertices)

    # Can be broken down into two fewer triangles than vertices
    offset = 0
    while len(vertices) > 3:
        # Don't start at the same vertex every time (helps to avoid ugly thin
        # triangles.)
        offset = (offset + 1) % len(vertices)
        indices = range(offset, len(vertices)) + range(0, offset)
        
        for i in indices:
            vertex = vertices[i]
            # Find out whether it's an ear
            vertex_before = vertices[i - 1]
            try:
                vertex_after = vertices[i + 1]
            except IndexError:
                vertex_after = vertices[0]
                        
            # Internal corner? Not an ear
            angle = get_angle(vertex_before, vertex, vertex_after)
            if angle >= 0.0:
                continue
            
            # Would a triangle made from the two adjacent points cross any
            # other walls? Not an ear
            test_edge = (vertex_before, vertex_after)
            walls = []
            is_ear = True
            for j, vertex_a in enumerate(vertices):
                try:
                    vertex_b = vertices[j + 1]
                except IndexError:  # Loop back to the start
                    vertex_b = vertices[0]
                wall = vertex_a, vertex_b
                if lines_intersect(wall, test_edge):
                    is_ear = False
                    break
            if not is_ear:
                continue
            
            # The vertex is an ear; create a triangle from the adjacent points
            # and remove the vertex from the list
            triangle = vertex_before, vertex, vertex_after
            triangles.append(triangle)
            break
        else:
            # return triangles
            raise RuntimeError("No ears remaining")
        del vertices[i]
        
    # Remaining vertices make up the last triangle
    triangles.append(tuple(vertices))
    return triangles

def draw_rect(origin=(0.0, 0.0), size=(1.0, 1.0),
              tex_origin=(0.0, 0.0), tex_size=(1.0, 1.0), mode=GL_TRIANGLES):
    """Use OpenGL commands to draw a rectangle with the given specifications.
    
    """
    # Get extremes
    left = origin[0]
    right = origin[0] + size[0]
    bottom = origin[1]
    top = origin[1] + size[1]
    tex_left = tex_origin[0]
    tex_right = tex_origin[0] + tex_size[0]
    tex_bottom = tex_origin[1]
    tex_top = tex_origin[1] + tex_size[1]
    
    # Draw
    glBegin(mode)
    glTexCoord2f(tex_left, tex_bottom)
    glVertex2f(left, bottom)
    glTexCoord2f(tex_left, tex_top)
    glVertex2f(left, top)
    glTexCoord2f(tex_right, tex_top)
    glVertex2f(right, top)
    glTexCoord2f(tex_left, tex_bottom)
    glVertex2f(left, bottom)
    glTexCoord2f(tex_right, tex_top)
    glVertex2f(right, top)
    glTexCoord2f(tex_right, tex_bottom)
    glVertex2f(right, bottom)
    glEnd()
    