"""Simple radiosity implementation. Generates lightmap values by rendering 
the scene from the texel's point of view.

Based on: http://freespace.virgin.net/hugo.elias/radiosity/radiosity.htm

"""
import math

from pyglet.gl import *
import pyglet.image

import utils

# Size of canvas that the incident light will be rendered onto
INCIDENT_SAMPLE_SIZE = 256
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
                data += chr(0) * 3 + chr(255)  # RGBA
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
    _SHAPE_COMPENSATION_TEX = shape_compensation_map.get_texture()
    return _SHAPE_COMPENSATION_TEX
    
            
