"""Simple radiosity implementation. Generates lightmap values by rendering 
the scene from the texel's point of view.

Based on: http://freespace.virgin.net/hugo.elias/radiosity/radiosity.htm

"""
import math

from pyglet.gl import *
import pyglet.image

import view
import utils

# Size of canvas that the incident light will be rendered onto
INCIDENT_SAMPLE_SIZE = 256
# Check the size is valid
if not INCIDENT_SAMPLE_SIZE in [16, 64, 256, 1024]:
    raise ValueError("Incident sample size must be a power of 4")
# Useful multiples
QUARTER_SIZE = INCIDENT_SAMPLE_SIZE // 4
HALF_SIZE = INCIDENT_SAMPLE_SIZE // 2
THREEQ_SIZE = 3 * INCIDENT_SAMPLE_SIZE // 4

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

def get_compensation_tex():
    return get_shape_compensation_tex()

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
        glBegin(GL_TRIANGLES)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(0.0, 0.0)
        glTexCoord2f(0.0, 1.0)
        glVertex2f(0.0, 1.0)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(1.0, 1.0)
        glTexCoord2f(0.0, 0.0)
        glVertex2f(0.0, 0.0)
        glTexCoord2f(1.0, 1.0)
        glVertex2f(1.0, 1.0)
        glTexCoord2f(1.0, 0.0)
        glVertex2f(1.0, 0.0)
        glEnd()
    glDisable(GL_BLEND)
