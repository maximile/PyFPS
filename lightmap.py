import pyglet
from pyglet.gl import *
import utils

class Lightmap(object):
    def __init__(self, size):
        # Check size
        self.size = (int(round(size[0])), int(round(size[1])))
        for size_component in self.size:
            if not utils.is_power_of_two(size_component):
                raise ValueError("Size must be power of two")
        
        # Create an image
        self.image = pyglet.image.create(self.size[0], self.size[1])
        # Get format and pitch
        self.format = self.image.format
        self.pitch = self.image.pitch
        # Fill it with black
        tex_data = (chr(0) * 3 + chr(255)) * self.size[0] * self.size[1]
        self.image.set_data(self.format, self.pitch, tex_data)
        
        # Create another image to store in-progress data
        self.in_progress_image = pyglet.image.create(self.size[0], self.size[1])
        assert self.in_progress_image.format == self.format
        assert self.in_progress_image.pitch == self.pitch
        tex_data = (chr(127) * 3 + chr(255)) * self.size[0] * self.size[1]
        self.in_progress_image.set_data(self.format, self.pitch, tex_data)
        
        # Get the textures
        self.texture = self.image.get_texture()
        self.in_progress_texture = self.in_progress_image.get_texture()
    
    def set_value(self, texel, value):
        """Set the in-progress value at the given texel.
        
        texel: Texel coordinates (tuple of x and y)
        value: New texel colour (tuple of RGB floats 0.0-1.0)
        
        """
        # Get data for given value
        value_data = ""
        for channel_value in value:
            int_value = int(round(channel_value * 255.0))
            value_data += chr(int_value)
        value_data += chr(255)  # Alpha
        
        # Replace the texel data with the new value
        texel_index = texel[1] * self.size[0] + texel[0]
        data = self.in_progress_image.get_data(self.format, self.pitch)
        data_before = data[:texel_index * 4]
        data_after = data[(texel_index + 1) * 4:]
        new_data = data_before + value_data + data_after

        # Update the image
        self.in_progress_image.set_data(self.format, self.pitch, new_data)
        self.in_progress_texture = self.in_progress_image.get_texture()

        # Set tex attributes
        # We'll be scaling it down to average the pixels, so use linear
        # minification.
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.in_progress_texture.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
    
    def update_from_in_progress(self):
        """After setting pixel data using set_value, call this to update the
        main image from the in-progress version.
        
        """
        # Create a new image
        self.image = pyglet.image.create(self.size[0], self.size[1])
        assert self.image.format == self.format
        assert self.image.pitch == self.pitch
        
        # Fill it with the contents of the in-progress image
        in_progress_data = self.in_progress_image.get_data(self.format,
                                                           self.pitch) 
        self.image.set_data(self.format, self.pitch, in_progress_data)
        self.texture = self.image.get_texture()
        # Set tex attributes
        # We'll be scaling it down to average the pixels, so use linear
        # minification.
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.texture.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP)

        