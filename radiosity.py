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

class Radiosity(object):
    """Class for managing lightmap generation using radiosity.
    
    """
    def __init__(self, render_func, sample_size=256):
        # Function we call to draw the scene
        self.render_func = render_func

        # Check the size is valid - power of 4, less than 2048
        valid_sample_sizes = [16, 64, 256, 1024]
        if not sample_size in valid_sample_sizes:
            raise ValueError("Incident sample size must be one of: " +
                             ", ".join([str(i) for i in valid_sample_sizes]))
        # Size to render scene at to generate light map
        self.sample_size = sample_size
        
        # Map to apply Lambert lighting and correct for cubemap distortion
        self.multiplier_map = self._generate_multiplier_map_tex()
        
        # FBO and texture to sample to, and another to 'ping-pong' scale.
        maps = self._generate_incident_textures_and_fbos()
        self.sample_tex = maps[0][0]
        self.sample_fbo = maps[0][1]
        self.sample_tex_b = maps[1][0]
        self.sample_fbo_b = maps[1][1]
        
        # Info about how to render the cubemaps
        self.view_setups = self._generate_view_setups()
        
    def _generate_view_setups(self):
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

    def sample(self, position, heading, pitch):
        """Return the RGB value of the incident light at the given position.
        
        Renders the scene to a cubemap and gets the average of the pixels.
        
        """
        # Bind the main, full-size FBO
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, self.sample_fbo)

        # Draw each face of the cube map
        for setup in self.view_setups:
            # Setup matrix
            glViewport(*setup["viewport"])
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(90.0, 1.0, 0.001, 100.0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glEnable(GL_DEPTH_TEST)
            glRotatef(90.0, 0.0, 1.0, 0.0)
            glRotatef(-90.0, 1.0, 0.0, 0.0)
            glRotatef(utils.rad_to_deg(pitch) + setup["pitch"],
                      0.0, 1.0, 0.0)
            glRotatef(utils.rad_to_deg(heading) + setup["heading"],
                      0.0, 0.0, -1.0)
            glTranslatef(-position[0], -position[1], -position[2])
            
            # Draw the scene
            self.render_func()

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
        
        # Draw the map
        utils.draw_rect()
        
        # Reset the state
        glDisable(GL_BLEND)
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
        
        # We have the complete cube map in the main FBO. Draw it back and forth
        # between the two FBOs to accurately scale it down to 4x4 pixels.
        size = self.sample_size
        target = self.sample_fbo
        while size > 4:
            # Swap the target
            if target == self.sample_fbo:
                target = self.sample_fbo_b
            else:
                target = self.sample_fbo
            # Half the size
            size //= 2
            
            # Bind the target
            glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, target)
            
            # Setup matrix
            if target == self.sample_fbo:
                z = 256
            else:
                z = 128
            glViewport(0, 0, z, z)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0.0, z, 0.0, z, -1.0, 1.0)
            glMatrixMode(GL_MODELVIEW)
            # glLoadIdentity()
        
            # Draw the other texture
            if target == self.sample_fbo_b:
                texture = self.sample_tex
            else:
                texture = self.sample_tex_b
            glBindTexture(GL_TEXTURE_2D, texture.id)
            utils.draw_rect((0,0), (size, size))
        
        # The target texture now contains a tiny 4x4 hemicube in the corner.
        # Read the values back.
        pixel_data = (GLubyte * (4 * 4 * 4))(0)
        glReadPixels(0, 0, 4, 4, GL_RGBA, GL_UNSIGNED_BYTE, pixel_data)
        
        # Reset the state
        glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, 0)
        
        # Average the RGB values for the cubemap (so ignore the corner pixels)
        red_value = 0
        green_value = 0
        blue_value = 0
        for y in xrange(4):
            for x in xrange(4):
                if y in (0, 3) and x in (0, 3):
                    # Ignore corner pixels
                    continue
                pixel_index = y * 4 + x
                pixel_index *= 4  # 4 channels
                red_value += pixel_data[pixel_index]
                green_value += pixel_data[pixel_index + 1]
                blue_value += pixel_data[pixel_index + 2]
        # We've sampled 12 pixels. Divide by 255 to normalise, and divide
        # by a constant to correct for the multiplier map
        maximum = 0.40751633986928104
        red_average = red_value / 12.0 / 255.0 / 0.40751633986928104
        green_average = green_value / 12.0 / 255.0 / 0.40751633986928104
        blue_average = blue_value / 12.0 / 255.0 / 0.40751633986928104
        incident_light = (red_average, green_average, blue_average)

        # # Save the image
        # if target == self.sample_fbo_b:
        #     texture = self.sample_tex_b
        # else:
        #     texture = self.sample_tex
        # texture.save("/tmp/map.png")
        # print incident_light
        # raise RuntimeError()

        return incident_light
        
    def get_quadrant(self, pixel):
        """Given coords for the whole incident sample, return the quadrant.

        """
        quarter_size = self.sample_size / 4
        three_quarter_size = 3 * self.sample_size / 4
        if pixel[0] < quarter_size:
            if not quarter_size < pixel[1] < three_quarter_size:
                return None
            return LEFT
        if pixel[0] >= three_quarter_size:
            if not quarter_size < pixel[1] < three_quarter_size:
                return None
            return RIGHT
        if pixel[1] < quarter_size:
            if not quarter_size < pixel[0] < three_quarter_size:
                return None
            return TOP
        if pixel[1] >= three_quarter_size:
            if not quarter_size < pixel[0] < three_quarter_size:
                return None
            return BOTTOM
        return FRONT
    
    def get_quadrant_center(self, quadrant):
        half_size = self.sample_size // 2
        centers = {FRONT: (half_size, half_size),
                   TOP: (half_size, 0),
                   BOTTOM: (half_size, self.sample_size),
                   LEFT: (0, half_size),
                   RIGHT: (self.sample_size, half_size)}
        return centers[quadrant]

    def _generate_multiplier_map_tex(self):
        multiplier_map = pyglet.image.create(self.sample_size, self.sample_size)
        data = ""
        
        # Useful fractions
        half_sample_size = self.sample_size / 2.0
        quarter_sample_size = self.sample_size / 4.0
        sample_center = (half_sample_size, half_sample_size)
        
        # Iterate over pixels
        for y in xrange(self.sample_size):
            for x in xrange(self.sample_size):
                pixel = (x, y)
                
                # Which quadrant is the pixel in?
                quadrant = self.get_quadrant(pixel)
                if not quadrant:
                    data += chr(0) * 3 + chr(255)  # RGBA black
                    continue
                
                # Find the shape compensation value. First, find the distance
                # to the quadrant centre.
                center = self.get_quadrant_center(quadrant)
                distance = utils.get_length(pixel, center)
                # Get the angle between the camera direction and the texel
                angle = math.atan(distance / quarter_sample_size)
                compensation_value = math.cos(angle)

                # Find the Lambert cosine multiplier.
                distance = utils.get_length(pixel, sample_center)
                distance /= half_sample_size
                distance *= math.pi / 2.0
                lambert_value = math.cos(distance)
                if lambert_value < 0.0:
                    lambert_value = 0.0                
                
                # Get bytes for the image
                multiplier = compensation_value * lambert_value
                int_value = int(round(multiplier * 255.0))
                pixel_data = chr(int_value) * 3 + chr(255)  # RGBA
                data += pixel_data
        
        # Get the texture
        multiplier_map.set_data(multiplier_map.format,
                                multiplier_map.pitch, data)
        return multiplier_map.get_texture()
        

    def _generate_incident_textures_and_fbos(self):
        """Two FBOs used for lightmap generation.
        
        FBO A is the size of the incident sample; FBO B is half the size. The scene
        is drawn to A and then 'ping-ponged' between the two to scale it to 4px.
    
        """
        tex_fbo_list = []
        for size in self.sample_size, self.sample_size // 2:
            # Create the texture
            tex = pyglet.image.Texture.create_for_size(GL_TEXTURE_2D, size, size,
                                                       GL_RGBA)
            glBindTexture(GL_TEXTURE_2D, tex.id)
            # We'll be scaling it down to average the pixels, so use linear
            # minification.
            glEnable(GL_TEXTURE_2D)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)
                                                       
            # Create the FBO
            fbo = GLuint()
            glGenFramebuffersEXT(1, fbo)
            glBindFramebufferEXT(GL_FRAMEBUFFER_EXT, fbo)
            
            # Attach the texture to the FBO
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
