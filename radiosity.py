"""Simple radiosity implementation. Generates lightmap values by rendering 
the scene from the texel's point of view.

Based on: http://freespace.virgin.net/hugo.elias/radiosity/radiosity.htm

"""
import math

from pyglet.gl import *
import pyglet.image

import view
import utils

# Quadrant identifiers       0 1 2 3 4
FRONT = "FRONT"         #  0   +---+  
TOP = "TOP"             #  1 +-+ T +-+
BOTTOM = "BOTTOM"       #  2 | L F R |
LEFT = "LEFT"           #  3 +-+ B +-+
RIGHT = "RIGHT"         #  4   +---+

# Quadrant centres (i.e. the point the camera is looking at, not the centre
# of the area)
QUADRANT_CENTERS = {FRONT: (HALF_SIZE, HALF_SIZE),
                    TOP: (HALF_SIZE, 0),
                    BOTTOM: (HALF_SIZE, INCIDENT_SAMPLE_SIZE),
                    LEFT: (0, HALF_SIZE),
                    RIGHT: (INCIDENT_SAMPLE_SIZE, HALF_SIZE)}

def get_quadrant(texel):
"""Given coords for the whole incident sample, return the quadrant.

"""
if texel[0] < QUARTER_SIZE:
    if not QUARTER_SIZE < texel[1] < THREEQ_SIZE:
        return None
    return LEFT
if texel[0] >= THREEQ_SIZE:
    if not QUARTER_SIZE < texel[1] < THREEQ_SIZE:
        return None
    return RIGHT
if texel[1] < QUARTER_SIZE:
    if not QUARTER_SIZE < texel[0] < THREEQ_SIZE:
        return None
    return TOP
if texel[1] >= THREEQ_SIZE:
    if not QUARTER_SIZE < texel[0] < THREEQ_SIZE:
        return None
    return BOTTOM
return FRONT


class Radiosity(object):
    """Class for managing lightmap generation using radiosity.
    
    """
    def __init__(self, render_func, sample_size=128):
        # Function we call to draw the scene
        self.render_func = render_func

        # Check the size is valid - power of 4, less than 2048
        valid_sample_sizes = [16, 64, 256, 1024]
        if not sample_size in valid_sample_sizes:
            raise ValueError("Incident sample size must be one of: " +
                             ", ".join(valid_sample_sizes))
        # Size to render scene at to generate light map
        self._sample_size = sample_size
        
        # Map to apply Lambert lighting and correct for cubemap distortion
        self.multiplier_map = self._generate_multiplier_map()
        
        # FBO and texture to sample to, and another to 'ping-pong' scale.
        maps = self._generate_incident_textures_and_fbos()
        self.sample_tex_a = maps[0][0]
        self.sample_fbo_a = maps[0][1]
        self.sample_tex_b = maps[1][0]
        self.sample_fbo_b = maps[1][1]
        
        # Info about how to render the cubemaps
        self.view_setups = self._generate_view_setups()

    @property
    def sample_size(self):
        """Size of the texture that the sample cubemap is rendered to.
        
        """
        return _sample_size
    
    def _generate_view_setups():
        """A list of views that we need to render.
        
        Dictionaries, with:
        
            viewport: Args needed for glViewport command
            pitch: Camera rotation about Y axis
            heading: Camera rotation about local X axis
        
        """
        d = self.sample_size  # Just to be concise
        view_setups = [
               # Front
               {"viewport": (d // 4, d // 4, d // 2, d // 2),
               "pitch": 0.0, "heading": 0.0},
               # Top         
               {"viewport": (d // 4, 3 * d // 4, d // 2, d // 2),
               "pitch": 90.0, "heading": 0.0},
               # Bottom      
               {"viewport": (d // 4, -d // 4, d // 2, d // 2),
               "pitch": -90.0, "heading": 0.0},
               # Left        
               {"viewport": (-d // 4, d // 4, d // 2, d // 2),
               "pitch": 0.0, "heading": 90.0},
               # Right       
               {"viewport": (3 * d // 4, d // 4, d // 2, d // 2),
               "pitch": 0.0, "heading": -90.0}
        ]
        return view_setups

    def sample(position, heading, pitch):
        """Return the RGB value of the incident light at the given position.
        
        Renders the scene to a cubemap and gets the average of the pixels.
        
        """
        # Bind the main, full-size FBO
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.sample_fbo_a)

        # Draw each face of the cube map
        for setup in self.view_setups:
            # Setup matrix
            glViewport(*setup["viewport"])
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(90.0, 1.0, 0.1, 100.0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glRotatef(90.0, 0.0, 1.0, 0.0)
            glRotatef(-90.0, 1.0, 0.0, 0.0)
            glRotatef(utils.rad_to_deg(pitch) + setup["pitch"],
                      0.0, 1.0, 0.0)
            glRotatef(utils.rad_to_deg(heading) + setup["heading"],
                      0.0, 0.0, -1.0)
            glTranslatef(-position[0], -position[1], -position[2])
            
            # Draw the scene
            self.draw_func()

        # Draw multiplier map on top. First, set the matrix
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glViewport(0, 0, self.sample_size, self.sample_size)
        glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
        
        # Setup the state
        glDisable(GL_DEPTH_TEST)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_ZERO, GL_SRC_COLOR)
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.multiplier_map.id)
        utils.draw_rect()
        
        # Reset the state
        glDisable(GL_BLEND)
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
        
        # We have the complete cube map in the main FBO. Draw it back and forth
        # between the two FBOs to accurately scale it down to 4x4 pixels.
        size = self.sample_size
        target = self.sample_fbo_a
        while size > 4:
            # Swap the target
            if target == self.sample_fbo_a:
                target = self.sample_fbo_b
            else:
                target = self.sample_fbo_a
            # Half the size
            size //= 2
            
            # Bind the target
            glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, target)
            
            # Setup matrix
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glViewport(0, 0, size, size)
            glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)

            # Draw the other texture
            if target == self.sample_fbo_b:
                texture = self.sample_tex_a
            else:
                texture = self.sample_tex_b
            glBindTexture(GL_TEXTURE_2D, texture.id)
            utils.draw_rect()
        
        # The target texture now contains a tiny 4x4 hemicube in the corner.
        # Read the values back.
        pixel_data = (GLuint * 4 * 4)(0)
        glReadPixels(0, 0, 4, 4, GL_RGB, GL_UNSIGNED_INT, pixel_data)
        print pixel_data

        # Reset the state
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
        

_LAMBERT_TEX = None
def get_lambert_tex():
    """Greyscale image which should be multiplied with the incident light
    to apply Lambery's cosine law.
    
    """
    global _LAMBERT_TEX
    if _LAMBERT_TEX:
        return _LAMBERT_TEX
    
    # Not been generated yet; create a new one
    lambert_map = pyglet.image.create(INCIDENT_SAMPLE_SIZE,
                                      INCIDENT_SAMPLE_SIZE)
    data = ""
    
    # Pixels are multiplied by the cosine of the angle between the surface 
    # normal and the direction of the light.
    for y in xrange(INCIDENT_SAMPLE_SIZE):
        for x in xrange(INCIDENT_SAMPLE_SIZE):
            texel = (x, y)
            # Which quadrant is the texel in?
            quadrant = get_quadrant(texel)
            if not quadrant:
                data += chr(0) * 3 + chr(255)  # RGBA black
                continue
            
            # Find the distance to the quadrant centre
            center = QUADRANT_CENTERS[quadrant]
            distance = utils.get_length([texel, center])
            
            # TODO: I think this is completely wrong. The commented code is a
            # step in the right direction but still wrong.
            # # +----c--X-+  Find magnitude of angle a where X is the texel
            # # |    |a/  |  we're looking at (use distance from c to X)
            # # +----+/---+
            # if quadrant == FRONT:
            #     a = math.atan(distance / float(QUARTER_SIZE))
            # else:
            #     a = math.atan(distance / float(QUARTER_SIZE)) - math.pi / 2.0 
            # multiplier = abs(math.cos(a))
            distance = utils.get_length([texel, (HALF_SIZE, HALF_SIZE)])
            distance /= HALF_SIZE
            distance *= math.pi / 2.0
            multiplier = math.cos(distance)
            if multiplier < 0.0:
                multiplier = 0.0
            int_value = int(round(multiplier * 255.0))
            pixel_data = chr(int_value) * 3 + chr(255)  # RGBA
            data += pixel_data
    
    lambert_map.set_data(lambert_map.format,lambert_map.pitch, data)
    _LAMBERT_TEX = lambert_map.get_texture(rectangle=False)
    return _LAMBERT_TEX
    

_SHAPE_COMPENSATION_TEX = None
def get_shape_compensation_tex():
    """Greyscale image which should be multiplied with the incident light
    to compensate for the hemucube distortion.
    
    """
    global _SHAPE_COMPENSATION_TEX
    if _SHAPE_COMPENSATION_TEX:
        return _SHAPE_COMPENSATION_TEX
    
    # Not been generated yet; create a new one
    shape_compensation_map = pyglet.image.create(INCIDENT_SAMPLE_SIZE,
                                                 INCIDENT_SAMPLE_SIZE)
    data = ""
    
    # Pixels on a surface of the hemicube are multiplied by the cosine of the 
    # angle between the direction the camera is facing in, and the line from the
    # camera to the pixel.
    for y in xrange(INCIDENT_SAMPLE_SIZE):
        for x in xrange(INCIDENT_SAMPLE_SIZE):
            texel = (x, y)
            # Which quadrant is the texel in?
            quadrant = get_quadrant(texel)
            if not quadrant:
                data += chr(0) * 3 + chr(255)  # RGBA black
                continue
            
            # Find the distance to the quadrant centre
            center = QUADRANT_CENTERS[quadrant]
            distance = utils.get_length([texel, center])
            
            # Get the angle between the camera direction and the texel
            theta = math.atan(distance / float(QUARTER_SIZE))
            
            # Get bytes for the image
            multiplier = math.cos(theta)
            int_value = int(round(multiplier * 255.0))
            pixel_data = chr(int_value) * 3 + chr(255)  # RGBA
            data += pixel_data
            
    shape_compensation_map.set_data(shape_compensation_map.format,
                                    shape_compensation_map.pitch, data)
    _SHAPE_COMPENSATION_TEX = shape_compensation_map.get_texture(rectangle=False)
    
    return _SHAPE_COMPENSATION_TEX

_INCIDENT_TEX_A = None
_INCIDENT_FBO_A = None
_INCIDENT_TEX_B = None
_INCIDENT_FBO_B = None
def generate_incident_textures_and_fbos():
    """Two FBOs used for lightmap generation.
    
    FBO A is the size of the incident sample; FBO B is half the size. The scene
    is drawn to A and then 'ping-ponged' between the two to scale it to 4px.

    """
    tex_fbo_list = []
    for size in INCIDENT_SAMPLE_SIZE, HALF_SIZE:
        # Create the FBO
        fbo = GLuint()
        glGenFramebuffersEXT(1, fbo)
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, fbo)
        
        # Create the texture
        tex = pyglet.image.Texture.create_for_size(GL_TEXTURE_2D, size, size,
                                                   GL_RGBA)
        # Attach it to the FBO
        glBindTexture(GL_TEXTURE_2D, tex.id)
        glFramebufferTexture2DEXT(GL_FRAMEBUFFER_EXT, GL_COLOR_ATTACHMENT0_EXT,
                                  GL_TEXTURE_2D, tex.id, 0)
        status = glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT)
        assert status == GL_FRAMEBUFFER_COMPLETE_EXT
        
        # Reset the state
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
        
        # Add a tuple of texture and FBO to the list
        tex_fbo_list.append((tex, fbo))
    return tex_fbo_list
    
TEST_VAL = 0.0
def udpate_lightmap(wall, height, draw_func):
    global TEST_VAL
    # Get camera angle
    TEST_VAL += 0.02
    if TEST_VAL > 1.0:
        TEST_VAL = -1.0
    lerp_val = abs(TEST_VAL)

    position = (utils.lerp(wall[0][0], wall[1][0], lerp_val),
                utils.lerp(wall[0][1], wall[1][1], lerp_val),
                height)
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
    
    incident_fbo, incident_tex = get_incident_fbo()
    glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, incident_fbo)

    glEnable(GL_DEPTH_TEST)    
    glClearColor(0.0, 0.0, 0.0, 1.0)
    glClear(GL_COLOR_BUFFER_BIT)
    glClear(GL_DEPTH_BUFFER_BIT)
    
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
        glRotatef(utils.rad_to_deg(camera_angle) + setup["heading"], 0.0, 0.0, -1.0)
        glTranslatef(-position[0], -position[1], -position[2])
        draw_func()
    
    # Draw map on top
    glDisable(GL_DEPTH_TEST)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glViewport(0, 0, D, D)
    glOrtho(0.0, 1.0, 0.0, 1.0, -1.0, 1.0)
            
    compensation_tex = get_compensation_tex()
    lambert_tex = get_lambert_tex()
    glColor4f(1.0, 1.0, 1.0, 1.0)
    glEnable(GL_BLEND)
    glBlendFunc(GL_ZERO, GL_SRC_COLOR)
    glEnable(GL_TEXTURE_2D)
    for tex in lambert_tex, compensation_tex:
        glBindTexture(GL_TEXTURE_2D, tex.id)
        utils.draw_rect()
        glEnd()
    glDisable(GL_BLEND)
    
    glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)        
