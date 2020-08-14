######################################################################
#
# graphics.py
#
# Written for ENGR 028/CPSC 082: Mobile Robotics, Summer 2020
# Copyright (C) Matt Zucker 2020
#
######################################################################

import glfw
import OpenGL.GL
from CleanGL import gl
from PIL import Image
from ctypes import c_void_p
import numpy

######################################################################

ENUM_LOOKUP = dict([
    (int(value), name)
    for (name, value) in OpenGL.GL.__dict__.items()
    if isinstance(value, OpenGL.constant.IntConstant)
])

######################################################################

def mix(a, b, u):
    return a + u*(b-a)

######################################################################

def vec2(x, y):
    return numpy.array([x,y], dtype=numpy.float32)

def vec3(x, y, z):
    return numpy.array([x,y,z], dtype=numpy.float32)

def vec4(x, y, z, w):
    return numpy.array([x,y,z,w], dtype=numpy.float32)

######################################################################

def normalize(v):
    return v / numpy.linalg.norm(v)

######################################################################

def check_opengl_errors(context='doing stuff'):
    error = gl.GetError()
    if error:
        sys.stderr.write(context + ': OpenGL error: ' + gluErrorString(error))
        glfw.terminate()
        sys.exit(1)

######################################################################

def make_shader(stype, srcs):

    stype_str = 'vertex' if stype == gl.VERTEX_SHADER else 'fragment'

    if isinstance(srcs, list):
        source = ''.join(srcs)
    else:
        source = srcs

    shader = gl.CreateShader(stype)
    gl.ShaderSource(shader, source)
    gl.CompileShader(shader)

    status = gl.GetShaderiv(shader, gl.COMPILE_STATUS)

    if not status:
        info = gl.GetShaderInfoLog(shader)
        sys.stderr.write('error compiling {} shader:\n\n{}\n'.format(
            stype_str,
            info))
        sys.exit(1)

    check_opengl_errors('compiling {} shader'.format(stype_str))

    return shader

######################################################################

def make_program(vertex_shader, fragment_shader):

    if isinstance(vertex_shader, list) or isinstance(vertex_shader, str):
        vertex_shader = make_shader(gl.VERTEX_SHADER, vertex_shader)

    if isinstance(fragment_shader, list) or isinstance(fragment_shader, str):
        fragment_shader = make_shader(gl.FRAGMENT_SHADER, fragment_shader)

    program = gl.CreateProgram()
    gl.AttachShader(program, vertex_shader)
    gl.AttachShader(program, fragment_shader)
    gl.LinkProgram(program)

    check_opengl_errors('linking program')

    uniforms = dict()

    ucount = gl.GetProgramiv(program, gl.ACTIVE_UNIFORMS)

    for i in range(ucount):
        name, size, utype = gl.GetActiveUniform(program, i)
        name = name.decode('utf-8')
        uniforms[name] = gl.GetUniformLocation(program, name)

    return program, uniforms

######################################################################

INT_VEC_UFUNCS = [
    gl.Uniform1iv,
    gl.Uniform2iv,
    gl.Uniform3iv,
    gl.Uniform4iv
]

FLOAT_VEC_UFUNCS = [
    gl.Uniform1fv,
    gl.Uniform2fv,
    gl.Uniform3fv,
    gl.Uniform4fv
]

FLOAT_MAT_UFUNCS = {
    (2, 2): gl.UniformMatrix2fv,
    (3, 3): gl.UniformMatrix3fv,
    (4, 4): gl.UniformMatrix4fv
}

def set_uniform(location, value):

    if isinstance(value, int):
        value = numpy.array(value, dtype=numpy.int32)
    elif isinstance(value, float):
        value = numpy.array(value, dtype=numpy.float32)

    assert isinstance(value, numpy.ndarray)
    assert value.dtype == numpy.int32 or value.dtype == numpy.float32

    if value.dtype == numpy.float32 and len(value.shape) == 2:
        mfunc = FLOAT_MAT_UFUNCS[value.shape]
        mfunc(location, 1, gl.FALSE, value.transpose())
    else:
        count = value.size
        if value.dtype == numpy.float32:
            vfunc = FLOAT_VEC_UFUNCS[count-1]
        else:
            vfunc = INT_VEC_UFUNCS[count-1]
        vfunc(location, 1, value)

######################################################################

def setup_attrib(program, name, size, dtype, normalize, stride, offset):

    attrib_location = gl.GetAttribLocation(program, name)
    gl.VertexAttribPointer(attrib_location, size, dtype,
                          normalize, stride, c_void_p(offset))
    gl.EnableVertexAttribArray(attrib_location)

    return attrib_location

######################################################################

def perspective_matrix(fovy, aspect, near, far):

    f = 1.0/numpy.tan(fovy*numpy.pi/180)

    return numpy.array([
        [ f/aspect, 0, 0, 0 ],
        [ 0, f, 0, 0 ],
        [ 0, 0, (far+near)/(near-far), (2*far*near)/(near-far) ],
        [ 0, 0, -1, 0 ]
    ], dtype=numpy.float32)

######################################################################

def rotation_from_axes(idx0, axis0, idx1, axis1_suggestion):

    assert idx0 in range(3)
    assert idx1 in range(3)

    idx2 = 3 - idx0 - idx1

    assert axis0.dtype == numpy.float32 and axis0.shape == (3,)
    assert axis1_suggestion.dtype == numpy.float32 and axis1_suggestion.shape == (3,)

    R = numpy.empty((3, 3), dtype=numpy.float32)

    s = 1 if (idx1 == (idx0 + 1) % 3) else -1
    u = normalize(axis0)
    w = s*normalize(numpy.cross(u, axis1_suggestion))
    v = s*numpy.cross(w, u)

    R[idx0] = u
    R[idx1] = v
    R[idx2] = w

    return R

######################################################################

def look_at(eye, center, up, Rextra=None):

    R = rotation_from_axes(2, eye-center, 1, up)

    if Rextra is None:
        RR = R
    else:
        RR = numpy.dot(Rextra[:3, :3], R)

    M = numpy.eye(4, dtype=numpy.float32)

    M[:3, :3] = RR
    M[:3, 3] = -numpy.dot(R, eye)

    return M

######################################################################

def load_texture(filename, mode='RGB'):

    assert mode in ['RGB', 'RGBA']

    image = Image.open(filename)

    if image.mode != mode:
        image = image.convert(mode)

    array = numpy.array(image)

    h, w, nchan = array.shape
    assert nchan == len(mode)

    texid = gl.GenTextures(1)

    gl.BindTexture(gl.TEXTURE_2D, texid)
    gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR)
    gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR)
    gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE)
    gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE)


    internal_fmt = gl.SRGB if mode == 'RGB' else gl.SRGB_ALPHA
    fmt = gl.RGB if mode == 'RGB' else gl.RGBA

    gl.TexImage2D(gl.TEXTURE_2D, 0, internal_fmt, w, h, 0,
                 fmt, gl.UNSIGNED_BYTE, array[::-1])
    gl.GenerateMipmap(gl.TEXTURE_2D)

    check_opengl_errors('load texture {}'.format(filename))

    return texid

######################################################################

class IndexedPrimitives:

    TYPE_LOOKUP = {
        numpy.dtype('uint8'):  gl.UNSIGNED_BYTE,
        numpy.dtype('uint16'): gl.UNSIGNED_SHORT,
        numpy.dtype('uint32'): gl.UNSIGNED_INT,
    }
    
    program = None

    @classmethod
    def static_init(cls):

        vertex_src = '''

        #version 330

        uniform mat4 perspective;
        uniform mat4 view;
        uniform mat4 model;

        in vec3 vertexPosition;
        in vec3 vertexNormal;
        in vec2 vertexTexCoord;

        out vec3 fragPos;
        out vec3 fragNormal;
        out vec2 fragTexCoord;

        void main() {

            vec4 mPos = model * vec4(vertexPosition, 1.0);
            gl_Position = perspective * view * mPos;

            fragPos = mPos.xyz;
            fragNormal = mat3(model) * vertexNormal;
            fragTexCoord = vertexTexCoord;

        }
        '''
        
        fragment_src = '''
        #version 330

        uniform bool useTexture;
        uniform sampler2D materialTexture;
        uniform vec3 materialColor;
        uniform vec3 viewPos;
        uniform vec3 lightDir;

        in vec3 fragPos;
        in vec3 fragNormal;
        in vec2 fragTexCoord;
        
        out vec4 fragColor;

        void main() {

            vec3 color = materialColor;

            if (useTexture) {
                vec3 texColor = texture(materialTexture, fragTexCoord).xyz;
                color *= texColor;
            }

            vec3 normal = normalize(fragNormal);

            float nDotL = 0.5*dot(normal, lightDir) + 0.5;
            color *= mix(nDotL, 1, 0.05);

            vec3 viewDir = normalize(viewPos - fragPos);
            vec3 halfDir = normalize(viewDir + lightDir);
            float specAmount = pow(max(dot(normal, halfDir), 0.0), 40.0);
            color = mix(color, vec3(1.0), 0.75*specAmount);

            fragColor = vec4(color, 1.0);

        }
        '''

        cls.program, cls.uniforms = make_program(vertex_src, fragment_src)

        gl.UseProgram(cls.program)
        set_uniform(cls.uniforms['materialTexture'], 0)
        set_uniform(cls.uniforms['lightDir'], normalize(vec3(0.5, 0.25, 2)))

        check_opengl_errors('IndexedPrimitives program')

    @classmethod
    def faceted_triangles(cls, verts, indices, color, texture, model_pose=None):

        assert verts.dtype == numpy.float32
        
        assert len(verts.shape) == 2 and verts.shape[1] == 3
        
        assert len(indices.shape) == 2 and indices.shape[1] == 4
        

        UPPER_TEX_COORDS = numpy.array([
            [ 0, 0 ],
            [ 1, 1 ],
            [ 0, 1 ]
        ], dtype=numpy.float32)

        LOWER_TEX_COORDS = numpy.array([
            [ 0, 0 ],
            [ 1, 0 ],
            [ 1, 1 ]
        ], dtype=numpy.float32)

        vout = []
        
        for tri in indices:

            tri_verts = verts[tri[:3]]
            is_upper = tri[3]

            n = numpy.cross(tri_verts[1]-tri_verts[0], tri_verts[2]-tri_verts[0])
            n /= numpy.linalg.norm(n)

            tc = UPPER_TEX_COORDS if is_upper else LOWER_TEX_COORDS

            for v, t in zip(tri_verts, tc):
                vout.append( [ v[0], v[1], v[2], n[0], n[1], n[2], t[0], t[1] ] )


        positions_normals_texcoords = numpy.array(vout, dtype=numpy.float32)

        return cls(positions_normals_texcoords, gl.TRIANGLES,
                   None, color, texture, model_pose)

    @classmethod
    def sphere(cls, radius, slices, stacks, color, texture, model_pose=None):

        u = numpy.linspace(0, 1, slices+1)
        v = numpy.linspace(1, 0, stacks+1)
        inner_v = v[1:-1]

        lon = numpy.linspace(0, 2*numpy.pi, slices+1)
        lon[-1] = 0
        
        lat = numpy.linspace(numpy.pi/2, -numpy.pi/2, stacks+1)
        inner_lat = lat[1:-1]

        grid_lon, grid_lat = numpy.meshgrid(lon, inner_lat)
        grid_u, grid_v = numpy.meshgrid(u, inner_v)

        grid_lon = grid_lon.flatten()
        grid_lat = grid_lat.flatten()
        grid_u = grid_u.flatten()
        grid_v = grid_v.flatten()

        x = numpy.cos(grid_lon) * numpy.cos(grid_lat)
        y = numpy.sin(grid_lon) * numpy.cos(grid_lat)
        z = numpy.sin(grid_lat)

        grid_rows = stacks-1
        grid_cols = slices+1

        num_vertices = grid_rows*grid_cols + 2

        positions_normals_texcoords = numpy.zeros((num_vertices, 8),
                                                  dtype=numpy.float32)

        positions_normals_texcoords[:-2, 0] = x*radius
        positions_normals_texcoords[:-2, 1] = y*radius
        positions_normals_texcoords[:-2, 2] = z*radius

        positions_normals_texcoords[:-2, 3] = x
        positions_normals_texcoords[:-2, 4] = y
        positions_normals_texcoords[:-2, 5] = z

        positions_normals_texcoords[:-2, 6] = grid_u
        positions_normals_texcoords[:-2, 7] = grid_v

        positions_normals_texcoords[-2] = [ 0, 0, radius, 0, 0, 1, 0.5, 1 ]
        positions_normals_texcoords[-1] = [ 0, 0, -radius, 0, 0, -1, 0.5, 0 ]


        indices = []

        # TODO: vectorize this maybe
        for i0 in range(grid_rows-1):
            i1 = i0 + 1
            for j0 in range(grid_cols-1):
                j1 = j0 + 1
                idx00 = i0 * grid_cols + j0
                idx01 = i0 * grid_cols + j1
                idx10 = i1 * grid_cols + j0
                idx11 = i1 * grid_cols + j1
                indices.extend([idx00, idx10, idx11])
                indices.extend([idx11, idx01, idx00])

        lastrow = grid_cols*(grid_rows-1)
        top = grid_rows*grid_cols
        bottom = top + 1

        for j0 in range(grid_cols-1):
            j1 = j0 + 1
            indices.extend([top, j0, j1])
            indices.extend([bottom, j1+lastrow, j0+lastrow])
                
        indices = numpy.array(indices, dtype=numpy.uint32)
        
        return cls(positions_normals_texcoords, gl.TRIANGLES,
                   indices, color, texture, model_pose)

    @classmethod
    def cylinder(cls, radius, height, slices, stacks,
                 color, texture, model_pose=None):

        u = numpy.linspace(0, 1, slices+1)
        v = numpy.linspace(0, 1, stacks+1)

        lon = numpy.linspace(0, 2*numpy.pi, slices+1)
        lon[-1] = 0

        z = numpy.linspace(-0.5*height, 0.5*height, stacks+1)

        grid_lon, grid_z = numpy.meshgrid(lon, z)
        grid_u, grid_v = numpy.meshgrid(u, v)

        grid_lon = grid_lon.flatten()
        grid_z = grid_z.flatten()
        grid_u = grid_u.flatten()
        grid_v = grid_v.flatten()
        
        x = numpy.cos(grid_lon)
        y = numpy.sin(grid_lon)

        grid_rows = stacks+1
        grid_cols = slices+1
        grid_count = grid_rows*grid_cols

        num_vertices = grid_count + 2*(slices + 1)

        positions_normals_texcoords = numpy.zeros((num_vertices, 8),
                                                  dtype=numpy.float32)

        positions_normals_texcoords[:grid_count, 0] = x*radius
        positions_normals_texcoords[:grid_count, 1] = y*radius
        positions_normals_texcoords[:grid_count, 2] = grid_z

        positions_normals_texcoords[:grid_count, 3] = x
        positions_normals_texcoords[:grid_count, 4] = y
        positions_normals_texcoords[:grid_count, 5] = 0

        positions_normals_texcoords[:grid_count, 6] = grid_u
        positions_normals_texcoords[:grid_count, 7] = grid_v

        x = numpy.hstack([numpy.cos(lon[:-1]), [0]])
        y = numpy.hstack([numpy.sin(lon[:-1]), [0]])

        top_slice = slice(grid_count, grid_count+slices+1)

        positions_normals_texcoords[top_slice, 0] = x*radius
        positions_normals_texcoords[top_slice, 1] = y*radius
        positions_normals_texcoords[top_slice, 2] = 0.5*height

        positions_normals_texcoords[top_slice, 3] = 0
        positions_normals_texcoords[top_slice, 4] = 0
        positions_normals_texcoords[top_slice, 5] = 1

        positions_normals_texcoords[top_slice, 6] = 0.5 + 0.5*x
        positions_normals_texcoords[top_slice, 7] = 0.5 + 0.5*y

        bot_slice = slice(grid_count+slices+1, grid_count+2*(slices+1))

        positions_normals_texcoords[bot_slice, 0] = x*radius
        positions_normals_texcoords[bot_slice, 1] = y*radius
        positions_normals_texcoords[bot_slice, 2] = -0.5*height

        positions_normals_texcoords[bot_slice, 3] = 0
        positions_normals_texcoords[bot_slice, 4] = 0
        positions_normals_texcoords[bot_slice, 5] = -1

        positions_normals_texcoords[bot_slice, 6] = 0.5 + 0.5*x
        positions_normals_texcoords[bot_slice, 7] = 0.5 + 0.5*y
        

        indices = []

        # TODO: vectorize this maybe
        for i0 in range(grid_rows-1):
            i1 = i0 + 1
            for j0 in range(grid_cols-1):
                j1 = j0 + 1
                idx00 = i0 * grid_cols + j0
                idx01 = i0 * grid_cols + j1
                idx10 = i1 * grid_cols + j0
                idx11 = i1 * grid_cols + j1
                indices.extend([idx00, idx11, idx10])
                indices.extend([idx01, idx11, idx00])

        top = grid_count
        bot = grid_count + slices + 1

        for j0 in range(grid_cols-1):
            j1 = (j0 + 1) % slices
            indices.extend([top + j0, top + j1, top + slices])
            indices.extend([bot + j1, bot + j0, bot + slices])
                
        indices = numpy.array(indices, dtype=numpy.uint32)
        
        return cls(positions_normals_texcoords, gl.TRIANGLES,
                   indices, color, texture, model_pose)

    @classmethod
    def box(cls, dims, color, texture, model_pose=None):

        rx, ry, rz = dims * numpy.array([0.5, 0.5, 0.5])

        verts = numpy.array([
            [-rx, -ry, -rz],
            [ rx, -ry, -rz],
            [-rx,  ry, -rz],
            [ rx,  ry, -rz],
            [-rx, -ry,  rz],
            [ rx, -ry,  rz],
            [-rx,  ry,  rz],
            [ rx,  ry,  rz]
        ], dtype=numpy.float32)

        # TODO: redo so wraps around Z axis with X forward?
        indices = numpy.array([
            [ 0, 4, 6, 0 ],
            [ 0, 6, 2, 1 ],
            [ 1, 0, 2, 0 ],
            [ 1, 2, 3, 1 ],
            [ 5, 1, 3, 0 ],
            [ 5, 3, 7, 1 ],
            [ 4, 5, 7, 0 ],
            [ 4, 7, 6, 1 ],
            [ 1, 5, 4, 0 ],
            [ 1, 4, 0, 1 ],
            [ 6, 7, 3, 0 ],
            [ 6, 3, 2, 1 ]
        ], dtype=numpy.uint8)

        return cls.faceted_triangles(verts, indices, color, texture, model_pose)
    
    def __init__(self, positions_normals_texcoords, mode, indices, color,
                 texture, model_pose=None):
        
        # uniform for color

        if self.program is None:
            self.static_init()

        vdata = positions_normals_texcoords
        
        assert vdata.dtype == numpy.float32
        assert len(vdata.shape) == 2 and vdata.shape[1] == 8

        self.mode = mode

        self.vertex_buffer = gl.GenBuffers(1)
        gl.BindBuffer(gl.ARRAY_BUFFER, self.vertex_buffer)
        gl.BufferData(gl.ARRAY_BUFFER, vdata, gl.STATIC_DRAW)
        check_opengl_errors('IndexedPrimitives vertex buffer setup')

        if indices is None:
            self.element_buffer = None
            assert mode == gl.TRIANGLES
            assert len(positions_normals_texcoords) % 3 == 0
            self.element_count = len(positions_normals_texcoords)
            self.element_type = None
        else:
            self.element_buffer = gl.GenBuffers(1)
            self.element_count = indices.size
            self.element_type = self.TYPE_LOOKUP[indices.dtype]
            gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, self.element_buffer)
            gl.BufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW)
            check_opengl_errors('IndexedPrimitives element buffer setup')

        self.vao = gl.GenVertexArrays(1)
        gl.BindVertexArray(self.vao)
        gl.BindBuffer(gl.ARRAY_BUFFER, self.vertex_buffer)
        if self.element_buffer is not None:
            gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, self.element_buffer)
        check_opengl_errors('IndexedPrimitives vao setup')

        stride = 8*4

        setup_attrib(self.program, 'vertexPosition', 3, gl.FLOAT,
                     gl.FALSE, stride, 0)
        
        setup_attrib(self.program, 'vertexNormal', 3, gl.FLOAT,
                     gl.FALSE, stride, 3*4)
        
        setup_attrib(self.program, 'vertexTexCoord', 2, gl.FLOAT,
                     gl.FALSE, stride, 6*4)
        
        if model_pose is None:
            self.model_pose = numpy.eye(4, dtype=numpy.float32)
        else:
            assert model_pose.dtype == numpy.float32 and model_pose.shape == (4, 4)
            self.model_pose = model_pose

        self.color = color
        self.texture = texture
        
    def render(self):

        gl.UseProgram(self.program)

        set_uniform(self.uniforms['materialColor'], self.color)

        set_uniform(self.uniforms['model'], self.model_pose)

        if self.texture is None:
            set_uniform(self.uniforms['useTexture'], 0)
        else:
            set_uniform(self.uniforms['useTexture'], 1)
            gl.ActiveTexture(gl.TEXTURE0)
            gl.BindTexture(gl.TEXTURE_2D, self.texture)

        gl.BindVertexArray(self.vao)
        gl.BindBuffer(gl.ARRAY_BUFFER, self.vertex_buffer)
        
        if self.element_buffer is not None:
            gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, self.element_buffer)
            gl.DrawElements(self.mode, self.element_count, self.element_type, None)
        else:
            gl.DrawArrays(self.mode, 0, self.element_count)
            
        check_opengl_errors('IndexedPrimitives.render')
    
######################################################################

class FullscreenQuad:

    program = None
    uniforms = None
    
    vertex_buffer = None
    element_buffer = None
    vao = None

    @classmethod
    def static_init(cls):

        vertex_src = [
            '#version 330\n'
            'in vec2 vertexPosition;\n'
            'out vec3 color;\n'
            'out vec2 texCoord;\n'
            'void main()\n'
            '{\n'
            '    gl_Position = vec4(vertexPosition, 0.0, 1.0);\n'
            '    texCoord = 0.5*vertexPosition + 0.5;\n'
            '}\n'
        ]
        
        fragment_src = [
            '#version 330\n'
            'uniform sampler2D utex;\n'
            'in vec2 texCoord;\n'
            'out vec4 fragColor;\n'
            '\nvoid main() {\n'
            '  fragColor = texture(utex, texCoord);\n'
            '}\n'
        ]
        
        cls.program, cls.uniforms = make_program(vertex_src, fragment_src)

        gl.UseProgram(cls.program)

        set_uniform(cls.uniforms['utex'], 0)
        
        vertices = numpy.array([
            [-1, -1],
            [1, -1],
            [1, 1],
            [-1, 1],
        ], dtype=numpy.float32)

        indices = numpy.array([ 0, 1, 2, 0, 2, 3], dtype=numpy.uint8)

        cls.vertex_buffer = gl.GenBuffers(1)
        gl.BindBuffer(gl.ARRAY_BUFFER, cls.vertex_buffer)
        gl.BufferData(gl.ARRAY_BUFFER, vertices, gl.STATIC_DRAW)

        check_opengl_errors('vertex buffer setup')
        
        cls.element_buffer = gl.GenBuffers(1)
        gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, cls.element_buffer)
        gl.BufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW)

        check_opengl_errors('element buffer setup')

        cls.vao = gl.GenVertexArrays(1)

        gl.BindVertexArray(cls.vao)
        gl.BindBuffer(gl.ARRAY_BUFFER, cls.vertex_buffer)
        gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, cls.element_buffer)

        check_opengl_errors('vao setup')

        setup_attrib(cls.program, 'vertexPosition',
                     2, gl.FLOAT, gl.FALSE, 0, 0)

        check_opengl_errors('setting up vertexPosition')

        
    def __init__(self, texture):
        
        # uniforms for texture (sampler2D) and resolution (vec2)

        if self.program is None:
            self.static_init()

        self.texture = texture

    def render(self):        

        gl.ActiveTexture(gl.TEXTURE0)
        gl.BindTexture(gl.TEXTURE_2D, self.texture)
        
        gl.UseProgram(self.program)
        gl.BindVertexArray(self.vao)
        gl.BindBuffer(gl.ARRAY_BUFFER, self.vertex_buffer)
        gl.BindBuffer(gl.ELEMENT_ARRAY_BUFFER, self.element_buffer)
        gl.DrawElements(gl.TRIANGLES, 6, gl.UNSIGNED_BYTE, None)

        check_opengl_errors('FullscreenQuad.render')
    
######################################################################


class GlfwApp:

    MOUSE_BUTTON_INDEX = {
        glfw.MOUSE_BUTTON_LEFT: 0,
        glfw.MOUSE_BUTTON_MIDDLE: 1,
        glfw.MOUSE_BUTTON_RIGHT: 2
    }

    DEFAULT_WINDOW_HINTS = [
        (glfw.CONTEXT_VERSION_MAJOR, 3),
        (glfw.CONTEXT_VERSION_MINOR, 2),
        (glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE),
        (glfw.OPENGL_FORWARD_COMPAT, gl.TRUE),
        (glfw.DOUBLEBUFFER, gl.TRUE)
    ]

    ############################################################

    def __init__(self):

        if not glfw.init():
            print('GLFW initialization failed')
            sys.exit(1)

        self.window = None

        self.window_size = numpy.array([-1, -1], dtype=numpy.int32)
        self.framebuffer_size = numpy.array([-1, -1], dtype=numpy.int32)
        self.pixel_scale = numpy.array([1., 1.], dtype=numpy.float32)

        self.mouse_pos = numpy.array([-1, -1], dtype=numpy.float32)
        self.mouse_state = numpy.zeros(3, dtype=bool)
        self.mouse_down_pos = -numpy.ones((3, 2), dtype=numpy.float32)
        self.motion_always = False

        self.animating = False

        self.need_render = True

    ############################################################
        
    def run(self):

        assert self.window is not None

        while not glfw.window_should_close(self.window):
            
            if self.animating:
                glfw.poll_events()
            else:
                glfw.wait_events()
                
            if self.need_render or self.animating:
                self._render()

        glfw.destroy_window(self.window)

        glfw.terminate()

    ############################################################
        
    def _error_callback(self, error, description):
        sys.stderr.write('GLFW error: ' + description + '\n')

    ############################################################
        
    def _window_size_callback(self, window, w, h):
        self.window_size[:] = (w, h)
        self._framebuffer_size_updated()
        self._render()

    ############################################################
        
    def _key_callback(self, window, key, scancode, action, mods):
        self.key(key, scancode, action, mods)

    ############################################################

    def key(self, key, scancode, action, mods):
        pass
        
    ############################################################

    def _cursor_pos_callback(self, window, x, y):

        self.mouse_pos[:] = [
            x * self.pixel_scale[0],
            (self.window_size[1] - y) * self.pixel_scale[1]
        ]

        if numpy.any(self.mouse_state) or self.motion_always:
            self.motion(*self.mouse_pos)

    ############################################################

    def motion(self, x, y):
        pass

    ############################################################

    def _mouse_button_callback(self, window, button, action, mods):

        try:
            button_index = self.MOUSE_BUTTON_INDEX[button]
            is_press = (action == glfw.PRESS)
            self.mouse_state[button_index] = is_press
            if is_press:
                self.mouse_down_pos[button_index] = self.mouse_pos
            self.mouse(button_index, is_press, *self.mouse_pos)
        except KeyError:
            pass

    ############################################################

    def mouse(self, button_index, is_press, x, y):
        pass

    ############################################################
            
    def create_window(self, name, width, height, hints=DEFAULT_WINDOW_HINTS):
        
        self.window_size[:] = (width, height)

        try:
            monitor = glfw.get_primary_monitor()
            monitor_scale = glfw.get_monitor_content_scale(monitor)
            print('detected monitor_scale', monitor_scale)
        except:
            monitor_scale = (1.0, 1.0)

        create_window_size = numpy.round(self.window_size /
                                         monitor_scale).astype(numpy.int32)
        
        for hint, value in hints:
            glfw.window_hint(hint, value)
        
        self.window = glfw.create_window(
            create_window_size[0], create_window_size[1],
            name, None, None)

        if not self.window:
            print("create_window failed")
            glfw.terminate()
            sys.exit(1)
            
        self.window_size[:] = glfw.get_window_size(self.window)

        glfw.make_context_current(self.window)

        self._framebuffer_size_updated()

        glfw.set_key_callback(self.window, self._key_callback)
        glfw.set_window_size_callback(self.window, self._window_size_callback)
        glfw.set_cursor_pos_callback(self.window, self._cursor_pos_callback)
        glfw.set_mouse_button_callback(self.window, self._mouse_button_callback)

        check_opengl_errors('setup window')

    ############################################################

    def _framebuffer_size_updated(self):

        self.framebuffer_size[:] = glfw.get_framebuffer_size(self.window)

        self.pixel_scale = (self.framebuffer_size /
                            numpy.maximum(self.window_size, 1))

        self.need_render = True

        self.framebuffer_resized()

    ############################################################

    def framebuffer_resized(self):
        pass

    ############################################################
        
    def _render(self):
        self.render()
        self.need_render = False
        glfw.swap_buffers(self.window)

    ############################################################

    def render(self):
        clear_color = vec4(1, 0, 0.5, 1)
        gl.ClearBufferfv(gl.COLOR, 0, clear_color);
        
######################################################################

def _test_rotation_from_axes():

    for trial in range(100):
        
        axis0 = (numpy.random.random(3) * 2 - 1).astype(numpy.float32)
        
        while True:
            axis1 = (numpy.random.random(3) * 2 - 1).astype(numpy.float32)
            if numpy.abs(numpy.dot(axis0, axis1)) < 0.9:
                break
            
        idx0 = numpy.random.randint(3)
        idx1 = (idx0 + numpy.random.randint(2) + 1) % 3
        idx2 = 3 - idx0 - idx1
        
        R = rotation_from_axes(idx0, axis0, idx1, axis1)
        detR = numpy.linalg.det(R)


        u = normalize(axis0)
        v = normalize(axis1 - u * numpy.dot(u, axis1))
        
        print(idx0, axis0, idx1, axis1)
        print('should be 1:', detR)
        print('should be 1:', numpy.dot(R[idx0], axis0)/numpy.linalg.norm(axis0))
        print('should be 0:', numpy.dot(R[idx2], axis1))
        print('should be equal:', R[idx1], v)
        print()

        assert abs(detR - 1) < 1e-4
        assert numpy.isclose(numpy.dot(R[idx0], axis0), numpy.linalg.norm(axis0))
        assert abs(numpy.dot(R[idx2], axis1)) < 1e-5
        assert numpy.all(numpy.isclose(R[idx1], v, 1e-3))

if __name__ == '__main__':

    _test_rotation_from_axes()

    class DemoApp(GlfwApp):

        def __init__(self):
            super().__init__()
            self.create_window('Demo', 800, 600)

        def key(self, key, scancode, action, mods):
            if key == glfw.KEY_ESCAPE and action == glfw.PRESS:
                glfw.set_window_should_close(self.window, gl.TRUE)
            
    app = DemoApp()
    app.run()
