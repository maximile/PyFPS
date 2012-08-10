import math
import itertools
import pymunk
import pyglet
from pyglet.gl import *

import utils

class InvalidRoomError(Exception):
    """Raised when the room data isn't valid.
    
    """
    pass

class Room(object):
    def __init__(self, data):
        self.floor_height = data["floor_height"]
        self.ceiling_height = data["ceiling_height"]
        
        # Textures
        self.floor_texture = None
        self.ceiling_texture = None
        self.wall_texture = None
        floor_texture_path = data.get("floor_texture")
        if floor_texture_path:
            self.floor_texture = pyglet.image.load(floor_texture_path).get_texture()
        ceiling_texture_path = data.get("ceiling_texture")
        if ceiling_texture_path:
            self.ceiling_texture = pyglet.image.load(ceiling_texture_path).get_texture()
        wall_texture_path = data.get("wall_texture")
        if wall_texture_path:
            self.wall_texture = pyglet.image.load(wall_texture_path).get_texture()
        
        # Texture scales (1.0 means the texture is applied to 1m squares)
        self.floor_texture_scale = data.get("floor_texture_scale", 1.0)
        self.ceiling_texture_scale = data.get("ceiling_texture_scale", 1.0)
        
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
        
        # Triangulated data (generated later)
        self.floor_data = GLuint()
        glGenBuffers(1, self.floor_data)

        # self.triangles = []
        self.wall_triangles = []
    
    def add_to_space(self, space):
        for wall in self.walls:
            shape = pymunk.Segment(space.static_body, wall[0], wall[1], 0.0)
            space.add(shape)
    
    def generate_triangulated_data(self):
        """Generate triangles to draw floor, ceiling and walls.
        
        Must be called after shared walls have been set.
        
        """
        # self.triangles = utils.triangulate(self.vertices)
        
        # Get 2D triangles for the floor and ceiling
        self.triangles = utils.triangulate(self.vertices)
        # Put the vertex attributes in an interleaved array
        floor_data = []
        for triangle in self.triangles:
            for point in triangle:
                # 3D vertex coords
                floor_data.append(point[0])
                floor_data.append(point[1])
                floor_data.append(self.floor_height)
                # 2D texture coords
                floor_data.append(point[0])
                floor_data.append(point[1])
        # Put it in an array of GLfloats
        floor_data = (GLfloat*len(floor_data))(*floor_data)
        # Add the data to the FBO
        glBindBuffer(GL_ARRAY_BUFFER, self.floor_data)
        glBufferData(GL_ARRAY_BUFFER, sizeof(floor_data), floor_data,
                     GL_STATIC_DRAW)
        
        self.wall_triangles = self.get_wall_triangles()
    
    def get_wall_triangles(self):
        all_wall_triangles = []
        # Triangulate each wall
        for i, wall in enumerate(self.walls):
            # Build the walls points as if looking straight at it
            wall_triangles = []
            if i in self.shared_walls:
                other = self.shared_walls[i]
                # Wall above the opening?
                if other.ceiling_height < self.ceiling_height:
                    # Top left, going clockwise
                    top_left = wall[0][0], wall[0][1], self.ceiling_height
                    top_right = wall[1][0], wall[1][1], self.ceiling_height
                    bottom_right = wall[1][0], wall[1][1], other.ceiling_height
                    bottom_left = wall[0][0], wall[0][1], other.ceiling_height
                    tri_one = top_left, top_right, bottom_right
                    tri_two = top_left, bottom_right, bottom_left
                    wall_triangles.append(tri_one)
                    wall_triangles.append(tri_two)
                # Wall below the opening?
                if other.floor_height > self.floor_height:
                    # Top left, going clockwise
                    top_left = wall[0][0], wall[0][1], other.floor_height
                    top_right = wall[1][0], wall[1][1], other.floor_height
                    bottom_right = wall[1][0], wall[1][1], self.floor_height
                    bottom_left = wall[0][0], wall[0][1], self.floor_height
                    tri_one = top_left, top_right, bottom_right
                    tri_two = top_left, bottom_right, bottom_left
                    wall_triangles.append(tri_one)
                    wall_triangles.append(tri_two)
                    
            else:
                # Top left, going clockwise
                top_left = wall[0][0], wall[0][1], self.ceiling_height
                top_right = wall[1][0], wall[1][1], self.ceiling_height
                bottom_right = wall[1][0], wall[1][1], self.floor_height
                bottom_left = wall[0][0], wall[0][1], self.floor_height
                
                tri_one = top_left, top_right, bottom_right
                tri_two = top_left, bottom_right, bottom_left
                wall_triangles.append(tri_one)
                wall_triangles.append(tri_two)
                
            all_wall_triangles.append(wall_triangles)
            
        return all_wall_triangles
            
    
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
            # angle = math.fmod(angle, math.pi)
            if angle > math.pi:
                angle -= math.pi * 2
            if angle < -math.pi:
                angle += math.pi * 2
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
            if utils.lines_intersect(wall_a, wall_b):
                raise InvalidRoomError("Walls intersect: %s, %s" %
                                       (wall_a, wall_b))
        
        # Check winding:
        self.check_winding()
        



