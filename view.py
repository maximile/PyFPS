import math
import pyglet
from pyglet.gl import *

from room import get_incident_fbo

import utils
from utils import rad_to_deg

SHARED_WALL_COLOR = 0.7, 0.7, 0.7, 1.0
WALL_COLOR = 0.0, 0.0, 0.0, 1.0
PLAYER_COLOR = 0.0, 0.7, 0.1, 1.0

# View modes
VIEW_2D = "VIEW_2D"
VIEW_3D = "VIEW_3D"
VIEW_INCIDENT = "VIEW_INCIDENT"

class View(object):
    def __init__(self, game):
        self.size = (0, 0)
        self.game = game
        self.w_down = False
        self.a_down = False
        self.s_down = False
        self.d_down = False
        self.view_mode = VIEW_2D
        self.first_time = True
        
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
    
    def project_2d(self):
        glLoadIdentity()
        glViewport(0, 0, self.size[0], self.size[1])
        glOrtho(0.0, 0.1, 0.0, 0.1, -1.0, 1.0)
    
    def draw_2d(self):
        glDisable(GL_DEPTH_TEST)
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

    def project_3d(self):
        glViewport(0, 0, self.size[0], self.size[1])
        glMatrixMode(GL_PROJECTION)
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

    def draw_3d(self):
        glEnable(GL_DEPTH_TEST)
             
        for room in self.game.rooms:

            # Room data geometry
            geo_count_texture = [(room.floor_data_vbo,
                                  room.floor_data_count,
                                  room.floor_texture),
                                 (room.ceiling_data_vbo,
                                  room.ceiling_data_count,
                                  room.ceiling_texture)]
            # Setup the state
            glColor4f(1.0, 1.0, 1.0, 1.0)
            for geo_vbo, count, texture in geo_count_texture:
                # Draw the floor. First, setup the state
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, texture.id)
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
                glDisable(GL_TEXTURE_2D)

            # WALLS: Setup the state
            glColor4f(1.0, 1.0, 1.0, 1.0)
            # Draw the floor. First, setup the state
            glEnable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0_ARB)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, room.wall_texture.id)
            glActiveTexture(GL_TEXTURE1_ARB)
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, room.lightmap_texture.id)
            
            # Draw the geometry
            glEnableClientState(GL_VERTEX_ARRAY)
            glBindBuffer(GL_ARRAY_BUFFER, room.wall_data_vbo)
            glVertexPointer(3, GL_FLOAT, 7 * sizeof(GLfloat), 0)
            glClientActiveTexture(GL_TEXTURE0_ARB)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glTexCoordPointer(2, GL_FLOAT, 7 * sizeof(GLfloat),
                              3 * sizeof(GLfloat))
            glClientActiveTexture(GL_TEXTURE1_ARB)
            glEnableClientState(GL_TEXTURE_COORD_ARRAY)
            glTexCoordPointer(2, GL_FLOAT, 7 * sizeof(GLfloat),
                              5 * sizeof(GLfloat))
            glDrawArrays(GL_TRIANGLES, 0, room.wall_data_count)
            # Reset the state
            glDisableClientState(GL_VERTEX_ARRAY)
            glDisableClientState(GL_TEXTURE_COORD_ARRAY)
            glDisable(GL_TEXTURE_2D)
            glActiveTexture(GL_TEXTURE0_ARB)
            glClientActiveTexture(GL_TEXTURE0_ARB)
            glActiveTexture(GL_TEXTURE0_ARB)
            
            glDisable(GL_TEXTURE_2D)
                    
            # Draw meshes
            for mesh in room.meshes:
                # Setup state
                glEnable(GL_TEXTURE_2D)
                glBindTexture(GL_TEXTURE_2D, mesh.texture.id)
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
                glDisable(GL_TEXTURE_2D)
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
        glPopMatrix()
                
    def draw_incident_fbo(self):
        incident_fbo, incident_tex = get_incident_fbo()
        
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, incident_tex.id)
        glBegin(GL_TRIANGLES)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(2.0, 2.0)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(2.0, 20.0)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(20.0, 20.0)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(2.0, 2.0)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(20.0, 20.0)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(20.0, 2.0)
        glEnd()
    
    test = 0.0
    def project_incident(self):
        # Get camera angle
        room = self.game.rooms[3]
        wall = room.walls[0]
        self.test += 0.02
        if self.test > 1.0:
            self.test = -1.0
        lerp_val = abs(self.test)

        position = (utils.lerp(wall[0][0], wall[1][0], lerp_val),
                    utils.lerp(wall[0][1], wall[1][1], lerp_val),
                    (room.floor_height + room.ceiling_height) / 2.0)
        wall_angle = math.atan2(wall[1][1] - wall[0][1],
                                wall[1][0] - wall[0][0])
        camera_angle = wall_angle - math.pi / 2.0
        
        D = 256
        view_setups = [
               # Front
               {"viewport": (D/4, D/4, D/2, D/2), "pitch": 0.0, "heading": 0.0},
                # Top
               {"viewport": (D/4, 3*D/4, D/2, D/2), "pitch": 90.0, "heading": 0.0},
                # Bottom
               {"viewport": (D/4, -D/4, D/2, D/2), "pitch": -90.0, "heading": 0.0},
                # Left
               {"viewport": (-D/4, D/4, D/2, D/2), "pitch": 0.0, "heading": 90.0},
                # Right
               {"viewport": (3*D/4, D/4, D/2, D/2), "pitch": 0.0, "heading": -90.0},
        ]
        
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT)
        for setup in view_setups:
            # Setup matrix
            glViewport(*setup["viewport"])
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(90.0, 1.0, 0.1, 100.0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glRotatef(90.0, 0.0, 1.0, 0.0)
            glRotatef(-90.0, 1.0, 0.0, 0.0)
            glRotatef(setup["pitch"], 0.0, 1.0, 0.0)
            glRotatef(rad_to_deg(camera_angle) + setup["heading"], 0.0, 0.0, -1.0)
            glTranslatef(-position[0], -position[1], -position[2])
            self.draw_3d()

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
                
        for matrix_mode in GL_PROJECTION, GL_MODELVIEW:
            glMatrixMode(matrix_mode)
            glPushMatrix()
        
        if self.view_mode == VIEW_2D:
            self.project_2d()
            self.draw_2d()
        elif self.view_mode == VIEW_3D:
            self.project_3d()
            self.draw_3d()
        elif self.view_mode == VIEW_INCIDENT:
            self.project_2d()
            self.draw_incident_fbo()
        
        # Draw to FBO
        incident_fbo, incident_tex = get_incident_fbo()
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, incident_fbo)
        glClear(GL_COLOR_BUFFER_BIT)
        self.project_incident()
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
        # 
        # # Draw FBO to screen
        # incident_fbo, incident_tex = get_incident_fbo()
        # if self.first_time:
        #     incident_tex.save("/tmp/fbo.png")
        #     self.first_time = False        
        
        
        for matrix_mode in GL_PROJECTION, GL_MODELVIEW:
            glMatrixMode(matrix_mode)
            glPopMatrix()
            
