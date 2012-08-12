import pyglet
from pyglet.gl import * 

class Mesh(object):
    def __init__(self, data, room):
        path = data["path"]
        self.position = tuple(data["position"])  # 3D coords
        if len(self.position) == 2:
            self.position = (self.position[0], self.position[1], room.floor_height)
        obj_data = open(path).read()
        texture_path = data.get("texture", "textures/default.png")
        texture_image = pyglet.image.load(texture_path)
        self.texture = texture_image.get_mipmapped_texture()
        
        # We can't start putting together the actual vertex data until we've
        # read the whole file, so populate these lists with data from the file
        vertices = []  # Tuples of xyz coords (always 3 components)
        tex_coords = []  # Tuples of texture coordinates, 2 components
        faces = []  # Indexes of vertices making up the faces, 3 or 4
        
        for line in obj_data.split("\n"):
            if line.startswith("v "):
                # Vertex position data; get three floats
                vertex_components = (float(string_rep) for
                                     string_rep in line[2:].split(" "))
                vertices.append(tuple(vertex_components))
            elif line.startswith("f "):
                face_data = line[2:].split(" ")
                corners = []  # Three or four items
                for vertex_data in face_data:  # e.g. 1/2/3
                    # Subtract one from indexes because they start at one
                    vertex_data = [int(string_rep) - 1 for
                                   string_rep in vertex_data.split("/")]
                    # vertex_index, normal_index, tex_coord_index = vertex_data
                    corners.append(tuple(vertex_data))
                faces.append(tuple(corners))
            elif line.startswith("vt "):
                # Vertex position data; get three floats
                tex_coord_components = [float(string_rep) for
                                        string_rep in line[3:].split(" ")]
                tex_coords.append(tuple(tex_coord_components))
                
        # Now start assembling the intermediate data structures
        vertex_data = []
        for face in faces:
            face_verts = [vertices[corner[0]] for corner in face]
            face_tex_coords = [tex_coords[corner[1]] for corner in face]
            # Triangulate quads
            if len(face_verts) == 3:
                for corner_vert, corner_tex_coords in zip(face_verts, face_tex_coords):
                    vertex_data.extend(corner_vert)
                    vertex_data.extend(corner_tex_coords)
            elif len(face_verts) == 4:
                triangle_indices = (0, 1, 2, 0, 2, 3)
                for i in triangle_indices:
                    vertex_data.extend(face_verts[i])
                    vertex_data.extend(face_tex_coords[i])
                # vertex_data.extend((face_verts[0], face_verts[1], face_verts[2]))
                # vertex_data.extend((face_tex_coords[0], face_tex_coords[1], face_tex_coords[2]))
                # vertex_data.extend((face_verts[0], face_verts[2], face_verts[3]))
                # vertex_data.extend((face_tex_coords[0], face_tex_coords[2], face_tex_coords[3]))
            else:
                raise RuntimeError("Invalid .obj data - %i verts in face" %
                                   len(face_verts))
        print vertex_data
        
        # Now put together the vertex buffer object
        self.data_vbo = GLuint()
        self.data_count = len(vertex_data)
        glGenBuffers(1, self.data_vbo)
        
        # Floor: put it in an array of GLfloats
        data = (GLfloat*self.data_count)(*vertex_data)
        # Add the data to the FBO
        glBindBuffer(GL_ARRAY_BUFFER, self.data_vbo)
        glBufferData(GL_ARRAY_BUFFER, sizeof(data), data,
                     GL_STATIC_DRAW)
        
        self.data_count /= 5
