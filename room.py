import math
import random
import itertools
import pymunk
import pyglet
from pyglet.gl import *

import utils
from utils import WALL_COLLISION_TYPE
from mesh import Mesh
from lightmap import Lightmap

# How to apply wall texture.
# Overall: no seams, minimal distortion, texture can wrap over corners
# Per wall: no seams, more distortion, texture repeats will always occur
#           at corners
WALL_TEXTURE_FIT_OVERALL = "overall"
WALL_TEXTURE_FIT_PER_WALL = "per_wall"

class InvalidRoomError(Exception):
    """Raised when the room data isn't valid.
    
    """
    pass

def smoothed(x):
    return -0.5 * math.cos(math.pi * x) + 0.5    

class Room(object):
    def __init__(self, data):
        self.floor_height = data["floor_height"]
        self.ceiling_height = data["ceiling_height"]
        
        # Floor texture.
        floor_texture_path = data.get("floor_texture", "textures/default.png")
        floor_texture_image = pyglet.image.load(floor_texture_path)
        self.floor_texture = floor_texture_image.get_mipmapped_texture()
        # Ceiling texture
        ceiling_texture_path = data.get("ceiling_texture",
                                        "textures/default.png")
        ceiling_texture_image = pyglet.image.load(ceiling_texture_path)
        self.ceiling_texture = ceiling_texture_image.get_mipmapped_texture()
        # Wall texture.
        wall_texture_path = data.get("wall_texture", "textures/default.png")
        wall_texture_image = pyglet.image.load(wall_texture_path)
        self.wall_texture = wall_texture_image.get_mipmapped_texture()
        self.wall_texture_fit = data.get("wall_texture_fit",
                                         WALL_TEXTURE_FIT_PER_WALL)
        
        # Texture scales (1.0 means the texture is applied to 1m squares)
        self.floor_texture_scale = data.get("floor_texture_scale", 1.0)
        self.ceiling_texture_scale = data.get("ceiling_texture_scale", 1.0)
        self.wall_texture_scale = data.get("wall_texture_scale", 1.0)
        
        # Texture rotation, degrees
        self.floor_texture_angle = data.get("floor_texture_angle", 0.0)
        self.ceiling_texture_angle = data.get("ceiling_texture_angle", 0.0)
        self.floor_texture_angle = utils.deg_to_rad(self.floor_texture_angle)
        self.ceiling_texture_angle = utils.deg_to_rad(
                                                    self.ceiling_texture_angle)
        
        # Light emission
        self.emit = data.get("emit", 0.0)
        
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
        
        # Work out bounding box
        min_x = max_x = self.vertices[0][0]
        min_y = max_y = self.vertices[0][1]
        for x, y in self.vertices:
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
        self.bounding_box = (min_x, max_x, min_y, max_y)

        # Texture coordinates for walls (uses same indexes as self.vertices)
        self.wall_texture_vertices = None
        self.wall_lightmap_vertices = None
        self.wall_texture_floor_height = None
        self.wall_texture_ceiling_height = None
        self.wall_lightmap_floor_height = None
        self.wall_lightmap_ceiling_height = None
        
        # Triangulated data (generated later)
        self.floor_data_vbo = GLuint()
        self.ceiling_data_vbo = GLuint()
        self.wall_data_vbo = GLuint()
        self.floor_data_count = 0
        self.ceiling_data_count = 0
        self.wall_data_count = 0
        glGenBuffers(1, self.floor_data_vbo)
        glGenBuffers(1, self.ceiling_data_vbo)
        glGenBuffers(1, self.wall_data_vbo)
        
        # Update texture and lightmap coords
        self.generate_wall_tex_coords()
        
        # Meshes
        self.meshes = []
        for mesh_data in data.get("meshes", []):
            self.meshes.append(Mesh(mesh_data, self))
        
        # self.triangles = []
        self.wall_triangles = []
    
    def contains_point(self, point):
        """True if the room contains the given 2D or 3D point.

        """
        # Three coords? Check Z first.
        if len(point) > 2:
            if not self.floor_height <= point[3] <= self.ceiling_height:
                return False

        # Check it's inside the boundaries
        distant_point = (0.0, 1e10)
        player_to_distance = ((point[0], point[1]), distant_point)
        # Count the times it crosses the room's boundary. Odd = inside.
        cross_count = 0
        for wall in self.walls:
            if utils.lines_intersect(player_to_distance, wall):
                cross_count += 1
        if cross_count % 2 == 1:
            return True
        else:
            return False

    def get_floor_ceiling_lm_coord(self, texel):
        """From a given texel, get the world space position.

        If the centre isn't contained, it'll try the corners instead.

        """
        min_x, max_x, min_y, max_y = self.bounding_box

        # Sample from the centre if that's inside the room.
        # If that fails, we'll also try every corner to get a value.
        # (Inaccurate but better than having uncoloured texels showing)
        center = (0.5, 0.5)
        corners = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
        for offset_x, offset_y in [center] + corners:
            ts_x = (texel[0] + offset_x) / float(self.floor_lightmap.size[0])
            ts_y = (texel[1] + offset_y) / float(self.floor_lightmap.size[1])
            # Get world space position
            x = (max_x - min_x) * ts_x + min_x
            y = (max_y - min_y) * ts_y + min_y
            if self.contains_point((x, y)):
                break
        else:
            # None of the centre or corners map to a part of the room
            return None

        return x, y

    def get_position_for_floor_lightmap_texel(self, texel):
        """

        """
        ws_coord = self.get_floor_ceiling_lm_coord(texel)
        if ws_coord is None:
            return None
        x, y = self.get_floor_ceiling_lm_coord(texel)
        pos = (x, y, self.floor_height)

        heading = 0.0  # Flat floor
        pitch = math.pi / 2.0
        return pos, heading, pitch    

    def get_position_for_ceiling_lightmap_texel(self, texel):
        """

        """
        ws_coord = self.get_floor_ceiling_lm_coord(texel)
        if ws_coord is None:
            return None
        x, y = self.get_floor_ceiling_lm_coord(texel)
        pos = (x, y, self.ceiling_height)

        heading = 0.0  # Flat floor
        pitch = math.pi / -2.0
        return pos, heading, pitch

    def get_position_for_wall_lightmap_texel(self, texel):
        """Get the position and normal for the part of the wall that the given
        lightmap texel applies to.
        
        Returns a position tuple (x, y, z) and a float for the normal (angle
        around the z axis; walls are always vertical)
        
        """
        # Get the texel in texture map space (0.0-1.0). Add 0.5 to use the
        # center of the texel instead of the corner.
        map_coords = ((texel[0] + 0.5) / float(self.wall_lightmap.size[0]),
                      (texel[1] + 0.5) / float(self.wall_lightmap.size[1]))
        
        # Find out which wall it's on
        for i, lightmap_wall in enumerate(self.lightmap_walls):
            if lightmap_wall[0] <= map_coords[0] < lightmap_wall[1]:
                break
        else:
            # Texel isn't applied to any wall
            return None
        wall = self.walls[i]
        
        # Find out how far along the wall it is
        ratio = ((map_coords[0] - lightmap_wall[0]) /
                 (lightmap_wall[1] - lightmap_wall[0]))
        # Use this to lerp along the wall
        x = utils.lerp(wall[0][0], wall[1][0], ratio)
        y = utils.lerp(wall[0][1], wall[1][1], ratio)
        
        # Lightmap texture height always reaches from floor to ceiling. Find
        # the z value.
        height_ratio = map_coords[1]
        z = utils.lerp(self.floor_height, self.ceiling_height, height_ratio)

        # Skip texels that won't get drawn (because the geometry is hidden)
        if i in self.shared_walls:
            other = self.shared_walls[i]
            if other.floor_height < z < other.ceiling_height:
                return None
        
        position = x, y, z
        wall_angle = math.atan2(wall[1][1] - wall[0][1], wall[1][0] - wall[0][0])
        normal = wall_angle - math.pi / 2.0
        pitch = 0.0  # No sloped walls
        return position, normal, pitch
    
    def add_to_space(self, space):
        for i, wall in enumerate(self.walls):
            shape = pymunk.Segment(space.static_body, wall[0], wall[1], 0.0)
            shape.collision_type = WALL_COLLISION_TYPE
            shape.room = self
            shape.wall_index = i
            space.add(shape)
    
    def generate_floor_and_ceiling_lightmaps(self):
        """Create lightmaps for the floor and ceiling.

        """
        width = 32.0
        height = 32.0

        self.floor_lightmap = Lightmap(width, height)
        self.ceiling_lightmap = Lightmap(width, height, (255, 255, 255))
        self.lightmaps.append((self.floor_lightmap,
                               self.get_position_for_floor_lightmap_texel))
        self.lightmaps.append((self.ceiling_lightmap,
                               self.get_position_for_ceiling_lightmap_texel))

    def generate_wall_lightmap(self):
        """Create a lightmap for the wall, and tex coords for it.
        
        """
        height = 32.0
        
        # Add up the wall lengths to find the width
        total_wall_length = 0.0
        for wall in self.walls:
            total_wall_length += utils.get_length(wall[0], wall[1])
        room_height = self.ceiling_height - self.floor_height
        width = (total_wall_length / room_height) * height
        
        # Round width to next power of two
        pot = 1
        while pot <= 2048:
            if width > pot:
                pot *= 2
            else:
                width = float(pot)
                break
        
        if width > 2048.0:
            height *= 2048.0 / width
            width = 2048.0
        
        # Create lightmap
        self.wall_lightmap = Lightmap(width, height)
        
        # Info to generate radiosity
        self.lightmaps.append((self.wall_lightmap,
                               self.get_position_for_wall_lightmap_texel))
        
    def generate_wall_tex_coords(self):
        """For each point along the walls, generate texture coordinates and
        lightmap coordinates.
        
        """
        # Y coords for textures
        self.wall_texture_floor_height = 0.0
        self.wall_texture_ceiling_height = 1.0 / self.wall_texture_scale
        self.wall_lightmap_floor_height = 0.0
        self.wall_lightmap_ceiling_height = 1.0
        
        self.wall_texture_vertices = []
        self.wall_lightmap_vertices = []
        
        # Always start at the left hand side
        self.wall_texture_vertices.append(0.0)
        self.wall_lightmap_vertices.append(0.0)
        
        # Add up the lengths of all the walls
        total_wall_length = 0.0
        for wall in self.walls:
            total_wall_length += utils.get_length(wall[0], wall[1])

        # Room height used to work out how many times we need to repeat
        # the texture
        room_height = self.ceiling_height - self.floor_height

        # Keep track of the length of wall covered
        wall_covered = 0.0
        for i, wall in enumerate(self.walls):
            # Get the texture x coords
            wall_length = utils.get_length(wall[0], wall[1])
            wall_covered += wall_length
            
            if self.wall_texture_fit == WALL_TEXTURE_FIT_PER_WALL:
                # Ratio of room height to wall length determines how many 
                # times the texture repeats.
                repeat_count = round(wall_length / room_height)
                
                # Account for the texture's dimensions
                repeat_count *= (float(self.wall_texture.height) /
                                 float(self.wall_texture.width))
                repeat_count /= self.wall_texture_scale
                if repeat_count < 1.0:
                    repeat_count = 1.0
                tex_coord = repeat_count
            elif self.wall_texture_fit == WALL_TEXTURE_FIT_OVERALL:
                # Ratio of room height to total wall length determines how many 
                # times the texture repeats.
                repeat_count = round(total_wall_length / room_height)
                
                # Account for the texture's dimensions
                repeat_count *= (float(self.wall_texture.height) /
                                 float(self.wall_texture.width))
                repeat_count /= self.wall_texture_scale
                if repeat_count < 1.0:
                    repeat_count = 1.0
                tex_coord = ((wall_covered / total_wall_length) * repeat_count)
            else:
                raise ValueError("Unknown texture fit value: %s"
                                 % self.wall_texture_fit)
    
            self.wall_texture_vertices.append(tex_coord)
            
            # Get lightmap coords
            self.wall_lightmap_vertices.append(wall_covered / total_wall_length)
        
    
    def generate_triangulated_data(self):
        """Generate triangles to draw floor, ceiling and walls.
        
        Must be called after shared walls have been set.
        
        """        
        # Get 2D triangles for the floor and ceiling
        self.triangles = utils.triangulate(self.vertices)
        # Put the vertex attributes in an interleaved array
        floor_data = []
        ceiling_data = []
        for triangle in self.triangles:
            for point in triangle:
                # Floor data
                # 3D vertex coords
                floor_data.append(point[0])
                floor_data.append(point[1])
                floor_data.append(self.floor_height)
                # 2D texture coords
                # Take the longest dimension as 1m
                floor_texture_ratio = (float(self.floor_texture.width) /
                                       float(self.floor_texture.height))
                if floor_texture_ratio < 1.0:
                    floor_texture_ratio = 1.0 / floor_texture_ratio
                # Apply rotation
                tex_x = (point[0] * math.cos(self.floor_texture_angle) -
                         point[1] * math.sin(self.floor_texture_angle))
                tex_y = (point[0] * math.sin(self.floor_texture_angle) +
                         point[1] * math.cos(self.floor_texture_angle))
                # Apply scale
                tex_x /= self.floor_texture_scale
                tex_y /= self.floor_texture_scale
                # Correct ratio and add to list
                floor_data.append(tex_x * floor_texture_ratio)
                floor_data.append(tex_y)
                # Lightmap coords
                min_x, max_x, min_y, max_y = self.bounding_box
                lm_x = (point[0] - min_x) / (max_x - min_x)
                lm_y = (point[1] - min_y) / (max_y - min_y)
                floor_data.extend([lm_x, lm_y])

            # Ceiling triangles need to be reversed to get the correct winding
            for point in reversed(triangle):
                # Ceiling data
                # 3D vertex coords
                ceiling_data.append(point[0])
                ceiling_data.append(point[1])
                ceiling_data.append(self.ceiling_height)
                # 2D texture coords
                # Take the longest dimension as 1m
                ceiling_texture_ratio = (float(self.ceiling_texture.width) /
                                         float(self.ceiling_texture.height))
                if ceiling_texture_ratio < 1.0:
                    ceiling_texture_ratio = 1.0 / ceiling_texture_ratio
                # Apply rotation
                tex_x = (point[0] * math.cos(self.ceiling_texture_angle) -
                         point[1] * math.sin(self.ceiling_texture_angle))
                tex_y = (point[0] * math.sin(self.ceiling_texture_angle) +
                         point[1] * math.cos(self.ceiling_texture_angle))
                # Apply scale
                tex_x /= self.ceiling_texture_scale
                tex_y /= self.ceiling_texture_scale
                # Correct ratio and add to list
                ceiling_data.append(tex_x * ceiling_texture_ratio)
                ceiling_data.append(tex_y)
                # Lightmap coords
                min_x, max_x, min_y, max_y = self.bounding_box
                lm_x = (point[0] - min_x) / (max_x - min_x)
                lm_y = (point[1] - min_y) / (max_y - min_y)
                ceiling_data.extend([lm_x, lm_y])
        
        # Floor: put it in an array of GLfloats
        self.floor_data_count = len(floor_data) / 7
        floor_data = (GLfloat * len(floor_data))(*floor_data)
        # Add the data to the FBO
        glBindBuffer(GL_ARRAY_BUFFER, self.floor_data_vbo)
        glBufferData(GL_ARRAY_BUFFER, sizeof(floor_data), floor_data,
                     GL_STATIC_DRAW)

        # Ceiling: put it in an array of GLfloats
        self.ceiling_data_count = len(ceiling_data) / 7
        ceiling_data = (GLfloat * len(ceiling_data))(*ceiling_data)
        # Add the data to the FBO
        glBindBuffer(GL_ARRAY_BUFFER, self.ceiling_data_vbo)
        glBufferData(GL_ARRAY_BUFFER, sizeof(ceiling_data), ceiling_data,
                     GL_STATIC_DRAW)
        
        # Now the walls. If we're okay with wraps around corners, we need to 
        # know the total wall length first.
        self.lightmaps = []
        self.generate_floor_and_ceiling_lightmaps()
        self.generate_wall_lightmap()
        if self.wall_texture_fit == WALL_TEXTURE_FIT_OVERALL:
            total_wall_length = 0.0
            for wall in self.walls:
                total_wall_length += utils.get_length(wall[0], wall[1])
            # Also keep track of the length of wall covered
            wall_covered = 0.0
        
        wall_data = []
        # Triangulate each wall
        for i, wall in enumerate(self.walls):
            # Shared walls might need to draw wall above and/or below the
            # other room.
            if i in self.shared_walls:
                other = self.shared_walls[i]
                # Wall above the opening?
                if other.ceiling_height < self.ceiling_height:
                    quad_data = self.get_wall_triangle_data(
                                   i, other.ceiling_height, self.ceiling_height)
                    wall_data.extend(quad_data)
                    
                # Wall below the opening?
                if other.floor_height > self.floor_height:
                    quad_data = self.get_wall_triangle_data(
                                   i, self.floor_height, other.floor_height)
                    wall_data.extend(quad_data)
            
            else:
                quad_data = self.get_wall_triangle_data(i)
                wall_data.extend(quad_data)
        
        # Wall: put it in an array of GLfloats
        self.wall_data_count = len(wall_data) // 5
        wall_data = (GLfloat * len(wall_data))(*wall_data)
        # Add the data to the FBO
        glBindBuffer(GL_ARRAY_BUFFER, self.wall_data_vbo)
        glBufferData(GL_ARRAY_BUFFER, sizeof(wall_data), wall_data,
                     GL_STATIC_DRAW)            
    
    def get_wall_triangle_data(self, wall_index, bottom=None, top=None):
        """FBO data for the given wall. Includes, vertex, tex coords and
        lightmap tex coords.
        
        """
        # Vertex coordinates
        wall = self.walls[wall_index]
        left = wall[0]
        right = wall[1]
        if not bottom:
            bottom = self.floor_height
        if not top:
            top = self.ceiling_height
        
        # We'll use the top and bottom values to get scaled texture coordinates.
        room_height = self.ceiling_height - self.floor_height
        top_ratio = (top - self.floor_height) / room_height
        bottom_ratio = (bottom - self.floor_height) / room_height
        
        # Texture coordinates
        tex_wall = self.texture_walls[wall_index]
        tex_left = tex_wall[0]
        tex_right = tex_wall[1]
        tex_top = utils.lerp(self.wall_texture_floor_height,
                             self.wall_texture_ceiling_height, top_ratio)
        tex_bottom = utils.lerp(self.wall_texture_floor_height,
                                self.wall_texture_ceiling_height, bottom_ratio)
        
        # Lightmap tex coords
        lightmap_wall = self.lightmap_walls[wall_index]
        lightmap_left = lightmap_wall[0]
        lightmap_right = lightmap_wall[1]
        lightmap_top = utils.lerp(self.wall_lightmap_floor_height,
                                  self.wall_lightmap_ceiling_height, top_ratio)
        lightmap_bottom = utils.lerp(self.wall_lightmap_floor_height,
                             self.wall_lightmap_ceiling_height, bottom_ratio)

        data = []
        
        # Two triangles. First:
        data.extend((left[0], left[1], top))
        data.extend((tex_left, tex_top))
        data.extend((lightmap_left, lightmap_top))

        data.extend((right[0], right[1], top))
        data.extend((tex_right, tex_top))
        data.extend((lightmap_right, lightmap_top))
        
        data.extend((right[0], right[1], bottom))
        data.extend((tex_right, tex_bottom))
        data.extend((lightmap_right, lightmap_bottom))
        
        # Second
        data.extend((left[0], left[1], top))
        data.extend((tex_left, tex_top))
        data.extend((lightmap_left, lightmap_top))
        
        data.extend((right[0], right[1], bottom))
        data.extend((tex_right, tex_bottom))
        data.extend((lightmap_right, lightmap_bottom))

        data.extend((left[0], left[1], bottom))
        data.extend((tex_left, tex_bottom))
        data.extend((lightmap_left, lightmap_bottom))
        
        return data
    
    def update(self, dt):
        return        
    
    def get_walls_from_vertices(self, vertices):
        """Pairs of vertices making up each wall.
        
        """
        walls = []
        for i, vertex_a in enumerate(vertices):
            try:
                vertex_b = vertices[i + 1]
            except IndexError:  # Loop back to the start
                vertex_b = vertices[0]
            walls.append((vertex_a, vertex_b))
        return walls
    
    @property
    def walls(self):
        """List of walls from the room's vertex data.
        
        >>> a = 0.0, 0.0  # c
        >>> b = 1.0, 0.0  # 
        >>> c = 0.0, 1.0  # a    b
        >>> Room((a, b, c)).walls == [(a, b), (b, c), (c, a)]
        True
        
        """
        return self.get_walls_from_vertices(self.vertices)
    
    @property
    def texture_walls(self):
        """Walls in texture coordinate space.
        
        """
        return self.get_walls_from_vertices(self.wall_texture_vertices)
    
    @property
    def lightmap_walls(self):
        """Walls in lightmap coordinate space.
        
        """
        return self.get_walls_from_vertices(self.wall_lightmap_vertices)
    
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
