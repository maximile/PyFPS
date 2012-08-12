import math
import pyglet
from pyglet.gl import *

import utils
from utils import rad_to_deg

SHARED_WALL_COLOR = 0.7, 0.7, 0.7, 1.0
WALL_COLOR = 0.0, 0.0, 0.0, 1.0
PLAYER_COLOR = 0.0, 0.7, 0.1, 1.0

class View(object):
    def __init__(self, game):
        self.size = (0, 0)
        self.game = game
        self.w_down = False
        self.a_down = False
        self.s_down = False
        self.d_down = False
        self.draw_func = self.draw_2d
        
    def update_player_movement_from_keys(self):
        movement_speed = 3.0
        x_speed = 0
        y_speed = 0
        if self.a_down:
            y_speed += movement_speed
        if self.d_down:
            y_speed -= movement_speed
        if self.w_down:
            x_speed += movement_speed
        if self.s_down:
            x_speed -= movement_speed
        self.game.player.movement = (x_speed, y_speed)        
    
    def draw_2d(self):
        glLoadIdentity()

        scale = 10.0
        glViewport(0, 0, self.size[0], self.size[1])
        glOrtho(0.0, 0.1, 0.0, 0.1, -1.0, 1.0)
        
        for room in self.game.rooms:
            glColor4f(0.8, 1.0, 0.9, 1.0)
            for triangle in room.triangles:
                glBegin(GL_LINE_LOOP)
                for vertex in triangle:
                    glVertex2f(vertex[0], vertex[1])
                glEnd()

            for i, wall in enumerate(room.walls):
                if i in room.shared_walls:
                    glColor4f(*SHARED_WALL_COLOR)
                else:
                    glColor4f(*WALL_COLOR)
                glBegin(GL_LINES)
                for vertex in wall:
                    glVertex2f(*vertex)
                glEnd()
            
            
        
        # Draw player
        player = self.game.player
        glColor4f(*PLAYER_COLOR)
        glPushMatrix()
        glTranslatef(player.position[0], player.position[1], 0.0)
        glRotatef(rad_to_deg(player.heading), 0.0, 0.0, 1.0)
        # Circle
        point_count = 12
        radius = player.radius
        glBegin(GL_LINE_LOOP)
        for i in range(point_count):
            theta = 2 * math.pi * (i / float(point_count))
            glVertex2f(radius * math.cos(theta), radius * math.sin(theta))
        glEnd()
            
        glBegin(GL_LINES)
        glVertex2f(-radius, 0.0)
        glVertex2f(radius * 2.5, 0.0)
        glVertex2f(0.0, -radius)
        glVertex2f(0.0, radius)
        glEnd()
        glPopMatrix()

    def draw_3d(self):
        glViewport(0, 0, self.size[0], self.size[1])
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        gluPerspective(45.0, float(self.size[0]) / float(self.size[1]),
                       0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        player = self.game.player
        glRotatef(90.0, 0.0, 1.0, 0.0)
        glRotatef(-90.0, 1.0, 0.0, 0.0)
        glRotatef(rad_to_deg(player.pitch), 0.0, 1.0, 0.0)
        glRotatef(rad_to_deg(player.heading), 0.0, 0.0, -1.0)
        glTranslatef(-player.position[0], -player.position[1],
                     -player.eye_height)
        
        for room in self.game.rooms:
            for i, wall in enumerate(room.walls):
                if i in room.shared_walls:
                    glColor4f(*SHARED_WALL_COLOR)
                else:
                    glColor4f(*WALL_COLOR)
                glBegin(GL_LINES)
                for vertex in wall:
                    glVertex3f(vertex[0], vertex[1], room.floor_height)
                glEnd()
            
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glBegin(GL_LINE_LOOP)
            for vertex in room.vertices:
                glVertex3f(vertex[0], vertex[1], room.ceiling_height)
            glEnd()
            
            glColor4f(0.0, 0.0, 0.0, 1.0)
            glBegin(GL_LINES)
            for vertex in room.vertices:
                glVertex3f(vertex[0], vertex[1], room.floor_height)
                glVertex3f(vertex[0], vertex[1], room.ceiling_height)
            glEnd()

            # Room data geometry
            geo_count_texture = [(room.floor_data_vbo,
                                  room.floor_data_count,
                                  room.floor_texture),
                                 (room.ceiling_data_vbo,
                                  room.ceiling_data_count,
                                  room.ceiling_texture),
                                 (room.wall_data_vbo,
                                  room.wall_data_count,
                                  room.wall_texture)]
            # Setup the state
            glColor4f(1.0, 1.0, 1.0, 1.0)
            for geo_vbo, count, texture in geo_count_texture:
                # Draw the floor. First, setup the state
                glEnable(texture.target)
                glBindTexture(texture.target, texture.id)
                # Draw the geometry
                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                glBindBuffer(GL_ARRAY_BUFFER, geo_vbo)
                glVertexPointer(3, GL_FLOAT, 5 * sizeof(GLfloat), 0)
                glTexCoordPointer(2, GL_FLOAT, 5 * sizeof(GLfloat),
                                  3 * sizeof(GLfloat))
                glDrawArrays(GL_TRIANGLES, 0, count)
                # Reset the state
                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_TEXTURE_COORD_ARRAY)
                glDisable(texture.target)
                    
            # Draw meshes
            for mesh in room.meshes:
                # Setup state
                glEnable(mesh.texture.target)
                glBindTexture(mesh.texture.target, mesh.texture.id)
                glPushMatrix()
                glTranslatef(*mesh.position)
                glEnableClientState(GL_VERTEX_ARRAY)
                glEnableClientState(GL_TEXTURE_COORD_ARRAY)
                # Draw the mesh
                glBindBuffer(GL_ARRAY_BUFFER, mesh.data_vbo)
                glVertexPointer(3, GL_FLOAT, 5 * sizeof(GLfloat), 0)
                glTexCoordPointer(2, GL_FLOAT, 5 * sizeof(GLfloat),
                                  3 * sizeof(GLfloat))
                glDrawArrays(GL_TRIANGLES, 0, mesh.data_count)
                # Reset the state
                glDisableClientState(GL_VERTEX_ARRAY)
                glDisableClientState(GL_TEXTURE_COORD_ARRAY)
                glDisable(mesh.texture.target)
                glPopMatrix()
        
        # Draw player
        player = self.game.player
        glColor4f(*PLAYER_COLOR)
        glPushMatrix()
        glTranslatef(player.position[0], player.position[1], 0.0)
        glRotatef(rad_to_deg(player.heading), 0.0, 0.0, 1.0)
        # Circle
        point_count = 12
        radius = player.radius
        glBegin(GL_LINE_LOOP)
        for i in range(point_count):
            theta = 2 * math.pi * (i / float(point_count))
            glVertex2f(radius * math.cos(theta), radius * math.sin(theta))
        glEnd()
            
        glBegin(GL_LINES)
        glVertex2f(-radius, 0.0)
        glVertex2f(radius * 2.5, 0.0)
        glVertex2f(0.0, -radius)
        glVertex2f(0.0, radius)
        glEnd()
        glPopMatrix()
        
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        

    def draw(self):
        glClearColor(1.0, 1.0, 1.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        glClear(GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LEQUAL)
        glPolygonOffset(1.0, 1.0)
        glEnable(GL_POLYGON_OFFSET_FILL)
        glEnable(GL_CULL_FACE)
        glFrontFace(GL_CW)

        self.draw_func()
