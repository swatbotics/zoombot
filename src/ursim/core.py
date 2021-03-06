######################################################################
#
# ursim/core.py
# 
# Written for ENGR 028/CPSC 082: Mobile Robotics, Summer 2020
# Copyright (C) Matt Zucker 2020
#
######################################################################
#
# Core 2D physics and graphics for robot simulation. Not for direct
# use by users.
#
######################################################################

import os
from datetime import timedelta
from importlib_resources import open_binary

import numpy
import Box2D as B2D
import svgelements 

from . import gfx
from .clean_gl import gl
from .datalog import DataLog
from .transform2d import Transform2D
from .motor import Motor

TAPE_COLORS = [
    gfx.vec3(0.3, 0.3, 0.9),
    gfx.vec3(0.6, 0.6, 0.6)
]

TAPE_COLOR_NAMES = [
    'blue', 'silver'
]

CARDBOARD_COLOR = gfx.vec3(0.8, 0.7, 0.6)

LINE_COLORS = TAPE_COLORS + [ CARDBOARD_COLOR ]


PYLON_COLOR_NAMES = [
    'orange', 'green'
]

PYLON_COLORS = [
    gfx.vec3(1.0, 0.5, 0),
    gfx.vec3(0, 0.8, 0),
]

BALL_COLOR = gfx.vec3(0.5, 0, 1)

CIRCLE_COLORS = [ BALL_COLOR ] + PYLON_COLORS

PYLON_RADIUS = 0.05
PYLON_HEIGHT = 0.23

PYLON_MASS = 0.250
PYLON_I = PYLON_MASS * PYLON_RADIUS * PYLON_RADIUS


TAPE_RADIUS = 0.025

TAPE_DASH_SIZE = 0.15

TAPE_POLYGON_OFFSET = 0.001

BALL_RADIUS = 0.15

BALL_MASS = 0.05
BALL_AREA = numpy.pi*BALL_RADIUS**2
BALL_DENSITY = BALL_MASS / BALL_AREA

WALL_THICKNESS = 0.005
WALL_HEIGHT = 0.5
WALL_Z = 0.03

CARDBOARD_DENSITY_PER_M2 = 0.45

BLOCK_MASS = 0.5
BLOCK_SZ = 0.1
BLOCK_COLOR = gfx.vec3(0.6, 0.5, 0.3)

ROOM_HEIGHT = 1.5

ROOM_COLOR = gfx.vec3(1, 0.97, 0.93)

ROBOT_BASE_RADIUS = 0.5*0.36
ROBOT_BASE_HEIGHT = 0.12
ROBOT_BASE_Z = 0.01
ROBOT_BASE_MASS = 2.5
ROBOT_BASE_I = 0.5*ROBOT_BASE_MASS*ROBOT_BASE_RADIUS**2

ROBOT_BASE_COLOR = gfx.vec3(0.1, 0.1, 0.1)

ROBOT_CAMERA_DIMS = gfx.vec3(0.08, 0.25, 0.04)
ROBOT_CAMERA_BOTTOM_Z = 0.18
ROBOT_CAMERA_LENS_Z = ROBOT_CAMERA_BOTTOM_Z + 0.5*ROBOT_CAMERA_DIMS[2]

ROBOT_WHEEL_OFFSET = 0.5*0.230
ROBOT_WHEEL_RADIUS = 0.035
ROBOT_WHEEL_WIDTH = 0.021

DEG = numpy.pi / 180

BUMP_ANGLE_RANGES = numpy.array([
    [ 20, 70 ],
    [ -25, 25 ],
    [ -70, -25 ]
], dtype=numpy.float32) * DEG

BUMP_DIST = 0.001

GRAVITY = 9.8

WHEEL_MAX_LATERAL_IMPULSE = 0.5 # m/(s*kg)

MOTOR_VEL_KP = 100 # V per m/s
MOTOR_VEL_KI = 200 # V per m

MOTOR_VEL_INT_MAX = 0.05 # m/s * s = m

# 2.5 gave plenty of issues with teleop
WHEEL_FORCE_MAX = 2.0
WHEEL_FORCE_MAX_STDDEV = 3.0

ODOM_FREQUENCY = 4

ODOM_NOISE_STDDEV = 0.02
ODOM_NOISE_THRESHOLD_VEL = 0.005

WHEEL_STOPPED_THRESHOLD_VEL = 0.15

# Wn = 0.05
SETPOINT_FILTER_B = numpy.array([0.07295966, 0.07295966])
SETPOINT_FILTER_A = numpy.array([-0.85408069])

# Wn = 0.1
VOLTAGE_FILTER_B = numpy.array([0.13672874, 0.13672874])
VOLTAGE_FILTER_A = numpy.array([-0.72654253])



LOG_NAMES = []

def log_var(s):
    global LOG_NAMES
    LOG_NAMES.append(s)
    return len(LOG_NAMES)-1

LOG_ROBOT_POS_X           = log_var('pos_x.pose.true')
LOG_ROBOT_POS_Y           = log_var('pos_y.pose.true')
LOG_ROBOT_POS_ANGLE       = log_var('angle.pose.true')
LOG_ODOM_POS_X            = log_var('pos_x.pose.odom')
LOG_ODOM_POS_Y            = log_var('pos_y.pose.odom')
LOG_ODOM_POS_ANGLE        = log_var('angle.pose.odom')
LOG_ROBOT_BUMP_LEFT       = log_var('bump.left')
LOG_ROBOT_BUMP_CENTER     = log_var('bump.center')
LOG_ROBOT_BUMP_RIGHT      = log_var('bump.right')
LOG_MOTORS_ENABLED        = log_var('motors_enabled')
LOG_ROBOT_CMD_VEL_FORWARD = log_var('forward_vel.cmd')
LOG_ROBOT_CMD_VEL_ANGULAR = log_var('angular_vel.cmd')
LOG_ROBOT_CMD_VEL_LWHEEL  = log_var('wheel_vel_l.cmd')
LOG_ROBOT_CMD_VEL_RWHEEL  = log_var('wheel_vel_r.cmd')
LOG_ROBOT_VEL_FORWARD     = log_var('forward_vel.true')
LOG_ROBOT_VEL_ANGLE       = log_var('angular_vel.true')
LOG_ROBOT_VEL_LWHEEL      = log_var('wheel_vel_l.true')
LOG_ROBOT_VEL_RWHEEL      = log_var('wheel_vel_r.true')
LOG_ODOM_VEL_LWHEEL       = log_var('wheel_vel_l.meas')
LOG_ODOM_VEL_RWHEEL       = log_var('wheel_vel_r.meas')
LOG_ODOM_VEL_FORWARD      = log_var('forward_vel.meas')
LOG_ODOM_VEL_ANGLE        = log_var('angular_vel.meas')

LOG_MOTOR_VEL_L           = log_var('motor_vel.l')
LOG_MOTOR_VEL_R           = log_var('motor_vel.r')

LOG_MOTOR_CURRENT_L       = log_var('motor_current.l')
LOG_MOTOR_CURRENT_R       = log_var('motor_current.r')

LOG_MOTOR_VOLTAGE_L       = log_var('motor_voltage.l')
LOG_MOTOR_VOLTAGE_R       = log_var('motor_voltage.r')

LOG_MOTOR_TORQUE_L        = log_var('motor_torque.l')
LOG_MOTOR_TORQUE_R        = log_var('motor_torque.r')

LOG_WHEEL_FORCE_L         = log_var('wheel_force.l')
LOG_WHEEL_FORCE_R         = log_var('wheel_force.r')

LOG_WHEEL_SKID_FORCE_L    = log_var('wheel_skid_force.l')
LOG_WHEEL_SKID_FORCE_R    = log_var('wheel_skid_force.r')


######################################################################

def vec_from_svg_color(color):
    return gfx.vec3(color.red, color.green, color.blue) / 255.

######################################################################

def match_svg_color(color, carray):

    if not isinstance(carray, numpy.ndarray):
        carray = numpy.array(carray)

    assert len(carray.shape) == 2 and carray.shape[1] == 3

    dists = numpy.linalg.norm(carray - color, axis=1)

    i = dists.argmin()

    return i, carray[i]

######################################################################

def b2ple(array):
    return tuple([float(ai) for ai in array])

def b2xform(transform, z=0.0):
    return gfx.rigid_2d_matrix(transform.position, transform.angle, z)


######################################################################

class SimObject:

    def __init__(self, world=None):
        
        self.gfx_objects = []

        self.world = world
        self.body = None
        self.body_linear_mu = None
        self.body_angular_mu = None

        self.gfx_objects = []

    def sim_update(self, time, dt):

        if self.body is None:
            return
        
        mg = self.body.mass * GRAVITY
        
        if self.body_linear_mu is not None:
            self.body.ApplyForceToCenter(
                (-self.body_linear_mu * mg ) * self.body.linearVelocity,
                True)

        if self.body_angular_mu is not None:
            self.body.ApplyTorque(
                (-self.body_angular_mu * mg) * self.body.angularVelocity,
                True)

    def destroy(self):
        
        if self.world is not None and self.body is not None:
            self.world.DestroyBody(self.body)
            self.body = None
            
        if self.world is None and self.body is not None:
            raise RuntimeError(str(self) + 'has body but no world!')

        for obj in self.gfx_objects:
            obj.destroy()

        self.gfx_objects = []

    def reset(self):
        pass

    def render(self):

        myxform = None
        
        for obj in self.gfx_objects:
            if self.body is not None and hasattr(obj, 'model_pose'):
                if myxform is None:
                    myxform = b2xform(self.body.transform)                    
                obj.model_pose = myxform
            obj.render()
        
######################################################################                
                
class Pylon(SimObject):

    static_gfx_object = None

    def __init__(self, world, position, cname):

        super().__init__(world=world)
        
        assert cname in PYLON_COLOR_NAMES

        self.body_linear_mu = 0.9

        cidx = PYLON_COLOR_NAMES.index(cname)

        self.color_name = cname
        self.color = PYLON_COLORS[cidx]
        self.material_id = (1 << (cidx+1))

        self.initialize(position)
        
    def initialize(self, position):

        self.destroy()

        self.body = self.world.CreateDynamicBody(
            position = b2ple(position),
            fixtures = B2D.b2FixtureDef(
                shape = B2D.b2CircleShape(radius=PYLON_RADIUS),
                density = 1.0,
                restitution = 0.25,
                friction = 0.6
            ),
            userData = self
        )

        self.body.massData = B2D.b2MassData(mass=PYLON_MASS,
                                            I=PYLON_I)

        self.orig_position = position

        if self.static_gfx_object is None:
            self.static_gfx_object = gfx.IndexedPrimitives.cylinder(
                PYLON_RADIUS, PYLON_HEIGHT, 32, 1,
                self.color,
                pre_transform=gfx.tz(0.5*PYLON_HEIGHT))
            
        self.gfx_objects = [self.static_gfx_object]
        
    def reset(self):
        self.initialize(self.orig_position)

    def render(self):
        self.static_gfx_object.color = self.color
        self.static_gfx_object.material_id = self.material_id
        super().render()

    def destroy(self):
        self.gfx_objects = []
        super().destroy()
        
######################################################################

class Ball(SimObject):

    static_gfx_object = None

    def __init__(self, world, position):

        super().__init__(world=world)
        
        self.body_linear_mu = 0.01
        
        self.initialize(position)

    def initialize(self, position):

        self.destroy()
        
        self.orig_position = position
        
        self.body = self.world.CreateDynamicBody(
            position = b2ple(position),
            fixtures = B2D.b2FixtureDef(
                shape = B2D.b2CircleShape(radius=BALL_RADIUS),
                density = BALL_DENSITY,
                restitution = 0.98,
                friction = 0.95
            ),
            userData = self
        )

        if self.static_gfx_object is None:
        
            self.static_gfx_object = gfx.IndexedPrimitives.sphere(
                BALL_RADIUS, 32, 24, 
                BALL_COLOR,
                pre_transform=gfx.tz(BALL_RADIUS),
                specular_exponent=60.0,
                specular_strength=0.125,
                material_id=int(1 << 3))
        
        self.gfx_objects = [ self.static_gfx_object ]

    def reset(self):
        self.initialize(self.orig_position)

    def destroy(self):
        self.gfx_objects = []
        super().destroy()
        
######################################################################

class Wall(SimObject):

    def __init__(self, world, p0, p1):

        super().__init__(world=world)

        self.body_linear_mu = 0.9 

        self.initialize(p0, p1)

    def initialize(self, p0, p1):

        self.destroy()
        
        self.orig_p0 = p0
        self.orig_p1 = p1
        
        position = 0.5*(p0 + p1)
        
        delta = p1 - p0
        theta = numpy.arctan2(delta[1], delta[0])

        length = numpy.linalg.norm(delta)
        
        dims = gfx.vec3(length,
                        WALL_THICKNESS, WALL_HEIGHT)


        self.dims = dims

        r = 0.5*BLOCK_SZ
        bx = 0.5*float(length) - 1.5*BLOCK_SZ

        shapes = [
            B2D.b2PolygonShape(box=(b2ple(0.5*numpy.array(dims[:2])))),
            B2D.b2PolygonShape(box=(r, r, (bx, 0), 0)),
            B2D.b2PolygonShape(box=(r, r, (-bx, 0), 0)),
        ]
            
        self.body = self.world.CreateDynamicBody(
            position = b2ple(position),
            angle = float(theta),
            shapes = shapes,
            shapeFixture = B2D.b2FixtureDef(density=1,
                                            restitution=0.1,
                                            friction=0.95),
            userData = self
        )


        rho = CARDBOARD_DENSITY_PER_M2

        mx = rho * (dims[1] * dims[2])
        Ix = mx * dims[0]**2 / 12

        Ib = BLOCK_MASS*BLOCK_SZ**2/6

        mass = mx + 2*BLOCK_MASS 
        I = Ix + 2*(Ib + BLOCK_MASS*bx**2)

        self.body_angular_mu = I-Ix
        
        self.body.massData = B2D.b2MassData(
            mass = mass,
            I = I
        )

        self.bx = bx
        self.dims = dims

        gfx_object = gfx.IndexedPrimitives.box(
            self.dims, CARDBOARD_COLOR,
            pre_transform=gfx.tz(WALL_Z + 0.5*self.dims[2]))

        self.gfx_objects = [gfx_object]

        for x in [-self.bx, self.bx]:

            block = gfx.IndexedPrimitives.box(
                gfx.vec3(BLOCK_SZ, BLOCK_SZ, BLOCK_SZ),
                BLOCK_COLOR,
                pre_transform=gfx.translation_matrix(
                    gfx.vec3(x, 0, 0.5*BLOCK_SZ)))

            self.gfx_objects.append(block)

    def reset(self):
        self.initialize(self.orig_p0, self.orig_p1)

######################################################################

class Box(SimObject):

    def __init__(self, world, dims, position, angle):

        super().__init__(world=world)
        
        self.initialize(dims, position, angle)

    def initialize(self, dims, position, angle):

        self.destroy()
        
        self.orig_position = position
        self.orig_angle = angle

        self.body = self.world.CreateDynamicBody(
            position = b2ple(position),
            angle = float(angle),
            fixtures = B2D.b2FixtureDef(
                shape = B2D.b2PolygonShape(box=(b2ple(0.5*numpy.array(dims[:2])))),
                density = 1.0,
                restitution = 0.1,
                friction = 0.6
            ),
            userData = self
        )

        rho = CARDBOARD_DENSITY_PER_M2

        mx = rho * (dims[1] * dims[2])
        my = rho * (dims[0] * dims[2])
        mz = rho * (dims[0] * dims[1])

        Ix = mx * dims[0]**2 / 12
        Iy = my * dims[1]**2 / 12
        Iz = mz*(dims[0]**2 + dims[1]**2)/12

        mass = 2*(mx + my + mz)
        I = 2 * (Ix + Iy + mx * dims[0]**2/4 + my * dims[1]**2/4 + Iz)

        self.body_linear_mu = 0.9
        self.body_angular_mu = I
        
        self.body.massData = B2D.b2MassData(
            mass = mass,
            I = I
        )

        self.dims = dims

        gfx_object = gfx.IndexedPrimitives.box(
            self.dims, CARDBOARD_COLOR,
            pre_transform=gfx.tz(0.5*self.dims[2]))

        self.gfx_objects = [gfx_object]
        
    def reset(self):
        self.initialize(self.dims, self.orig_position, self.orig_angle)

######################################################################

class Room(SimObject):

    floor_texture = None
    wall_texture = None
    
    def __init__(self, world, dims):

        super().__init__(world=world)

        self.initialize(dims)

    def initialize(self, dims):

        self.destroy()
        
        self.dims = dims

        shapes = []

        thickness = 1.0

        w = float(dims[0])
        h = float(dims[1])

        shapes.append(
            B2D.b2PolygonShape(
                box=(
                    thickness, 0.5*h+thickness,
                    (-thickness, 0.5*h), 0.0
                )
            )
        )
        
        shapes.append(
            B2D.b2PolygonShape(
                box=(
                    thickness, 0.5*h+thickness,
                    (w+thickness, 0.5*h), 0.0
                )
            )
        )

        shapes.append(
            B2D.b2PolygonShape(
                box=(
                    0.5*w+thickness, thickness,
                    (0.5*w, -thickness), 0.0
                )
            )
        )

        shapes.append(
            B2D.b2PolygonShape(
                box=(
                    0.5*w+thickness, thickness,
                    (0.5*w, h+thickness), 0.0
                )
            )
        )
        
        self.body = self.world.CreateStaticBody(
            userData = self,
            shapes = shapes
        )

        if self.floor_texture is None:
            self.floor_texture = gfx.load_texture(open_binary('ursim.textures', 'floor_texture.png'))
            gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT)
            gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT)

        if self.wall_texture is None:
            self.wall_texture = gfx.load_texture(open_binary('ursim.textures', 'wall_texture.png'))
            gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT)
            gl.TexParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT)
            
        w, h = self.dims

        vdata = numpy.array([
            [0, 0, 0, 0, 0, 1, 0, 0],
            [w, 0, 0, 0, 0, 1, w, 0],
            [w, h, 0, 0, 0, 1, w, h],
            [0, h, 0, 0, 0, 1, 0, h],
        ], dtype=numpy.float32)

        mode = gl.TRIANGLES

        indices = numpy.array([0, 1, 2, 0, 2, 3], dtype=numpy.uint8)

        floor_obj = gfx.IndexedPrimitives(
            vdata, mode, indices, 0.8*gfx.vec3(1, 1, 1),
            texture=self.floor_texture,
            specular_exponent = 40.0,
            specular_strength = 0.5)

        z = ROOM_HEIGHT

        verts = numpy.array([
            [ 0, 0, 0 ],
            [ w, 0, 0 ],
            [ 0, h, 0 ],
            [ w, h, 0 ],
            [ 0, 0, z ],
            [ w, 0, z ],
            [ 0, h, z ],
            [ w, h, z ],
        ], dtype=numpy.float32)

        indices = numpy.array([
            [ 0, 5, 1 ], 
            [ 0, 4, 5 ],
            [ 1, 7, 3 ], 
            [ 1, 5, 7 ],
            [ 3, 6, 2 ],
            [ 3, 7, 6 ],
            [ 2, 4, 0 ],
            [ 2, 6, 4 ],
        ], dtype=numpy.uint8)

        room_obj = gfx.IndexedPrimitives.faceted_triangles(
            verts, indices, ROOM_COLOR, texture=self.wall_texture)

        room_obj.specular_strength = 0.25

        self.gfx_objects = [ floor_obj, room_obj ]
        
    def reset(self):
        self.initialize(self.dims)


######################################################################

class TapeStrips(SimObject):

    SPECULAR_EXPONENTS = dict(blue=100.0, silver=30.0)
    SPECULAR_STRENGTHS = dict(blue=0.05, silver=0.7)

    def __init__(self, point_lists, cname):
        super().__init__()
        self.point_lists = point_lists

        self.specular_exponent = self.SPECULAR_EXPONENTS[cname]
        self.specular_strength = self.SPECULAR_STRENGTHS[cname]

        self.is_dashed = (cname == 'blue')
        self.material_id = int(cname == 'blue')

        cidx = TAPE_COLOR_NAMES.index(cname)
        self.color = TAPE_COLORS[cidx]
        self._rendered_point_lists = []

    def initialize(self, point_lists):

        self.destroy()
        
        self.point_lists = point_lists

        r = TAPE_RADIUS
        offset = gfx.vec3(0, 0, r)

        self.gfx_objects = []

        dashes = []

        for points in point_lists:

            points = points.copy() # don't modify original points

            deltas = points[1:] - points[:-1]
            segment_lengths = numpy.linalg.norm(deltas, axis=1)
            tangents = deltas / segment_lengths.reshape(-1, 1)

            is_loop = (numpy.linalg.norm(points[-1] - points[0]) < TAPE_RADIUS)

            if not is_loop:

                segment_lengths[0] += TAPE_RADIUS
                points[0] -= TAPE_RADIUS * tangents[0]
                deltas[0] = points[1] - points[0]

                segment_lengths[-1] += TAPE_RADIUS
                points[-1] += TAPE_RADIUS * tangents[-1]
                deltas[-1] = points[-1] - points[-2]

                desired_parity = 1

            else:

                desired_parity = 0

            if not self.is_dashed:

                dashes.append(points)

            else:

                total_length = segment_lengths.sum()

                num_dashes = int(numpy.ceil(total_length / TAPE_DASH_SIZE))
                if num_dashes % 2 != desired_parity:
                    num_dashes -= 1

                u = numpy.hstack(([numpy.float32(0)], numpy.cumsum(segment_lengths)))
                if not u[-1]:
                    continue

                u /= u[-1]

                cur_dash = [ points[0] ]
                cur_u = 0.0
                cur_idx = 0

                emit_dash = True


                for dash_idx in range(num_dashes):

                    target_u = (dash_idx + 1) / num_dashes

                    segment_end_u = u[cur_idx+1]

                    while segment_end_u < target_u:
                        cur_idx += 1
                        cur_dash.append(points[cur_idx])
                        segment_end_u = u[cur_idx+1]

                    segment_start_u = u[cur_idx]

                    assert segment_start_u < target_u
                    assert segment_end_u >= target_u

                    segment_alpha = ( (target_u - segment_start_u) /
                                      (segment_end_u - segment_start_u) )

                    cur_dash.append( gfx.mix(points[cur_idx],
                                             points[cur_idx+1],
                                             segment_alpha) )

                    if emit_dash:
                        dashes.append(numpy.array(cur_dash, dtype=numpy.float32))

                    emit_dash = not emit_dash

                    cur_dash = [ cur_dash[-1] ]

        npoints_total = sum([len(points) for points in dashes])

        vdata = numpy.zeros((2*npoints_total, 8), dtype=numpy.float32)
        
        vdata[:, 2] = TAPE_POLYGON_OFFSET
        vdata[:, 5]= 1

        vdata_offset = 0

        indices = []
                
        for points in dashes:

            prev_line_l = None
            prev_line_r = None

            points_l = []
            points_r = []

            # merge very close points in this
            deltas = points[1:] - points[:-1]
            norms = numpy.linalg.norm(deltas, axis=1)
            keep = numpy.hstack( ([ True ], norms > 1e-3) )

            points = points[keep]
            
            for i, p0 in enumerate(points[:-1]):

                p1 = points[i+1]

                tangent = gfx.normalize(p1 - p0)
                
                normal = numpy.array([-tangent[1], tangent[0]], dtype=numpy.float32)

                line = gfx.vec3(normal[0], normal[1], -numpy.dot(normal, p0))

                line_l = line - offset
                line_r = line + offset

                if i == 0:

                    points_l.append( p0 + r * (normal) )
                    points_r.append( p0 + r * (-normal) )

                else:

                    if abs(numpy.dot(line_l[:2], prev_line_l[:2])) > 0.999:

                        points_l.append( p0 + r * normal )
                        points_r.append( p0 - r * normal )

                    else:

                        linter, ldenom = gfx.line_intersect_2d(line_l, prev_line_l)
                        rinter, rdenom = gfx.line_intersect_2d(line_r, prev_line_r)

                        # TODO: parallel lines?

                        points_l.append( linter )
                        points_r.append( rinter ) 

                if i == len(points) - 2:

                    points_l.append( p1 + r * (normal) )
                    points_r.append( p1 + r * (-normal) )

                prev_line_l = line_l
                prev_line_r = line_r

                

            for i in range(len(points)-1):
                a = vdata_offset+2*i
                b = a + 1
                c = a + 2
                d = a + 3
                indices.extend([a, b, c])
                indices.extend([c, b, d])


            points_l = numpy.array(points_l)
            points_r = numpy.array(points_r)

            next_vdata_offset = vdata_offset + 2*len(points)

            vdata[vdata_offset:next_vdata_offset:2, :2] = points_l
            vdata[vdata_offset+1:next_vdata_offset:2, :2] = points_r
            vdata[vdata_offset:next_vdata_offset, 6:8] = vdata[vdata_offset:next_vdata_offset, 0:2]

            vdata_offset = next_vdata_offset

        indices = numpy.array(indices, dtype=numpy.uint32)

        gfx_object = gfx.IndexedPrimitives(vdata, gl.TRIANGLES,
                                           indices=indices,
                                           color=self.color,
                                           specular_exponent = self.specular_exponent,
                                           specular_strength = self.specular_strength,
                                           material_id=self.material_id)

        self.gfx_objects.append(gfx_object)

        self._rendered_point_lists = [p.copy() for p in self.point_lists]

    def reset(self):
        self.initialize(self.point_lists)

    def render(self):

        if len(self.point_lists) and not len(self.gfx_objects):
            self.reset()
        elif len(self.point_lists) != len(self._rendered_point_lists):
            self.reset()
        else:
            for pi, pj in zip(self.point_lists, self._rendered_point_lists):
                if len(pi) != len(pj) or not numpy.all(pi == pj):
                    self.reset()
                    break
            
        super().render()


######################################################################

def linear_angular_from_wheel_lr(wheel_lr_vel):

    l, r = wheel_lr_vel

    linear = (r+l)/2
    angular = (r-l)/(2*ROBOT_WHEEL_OFFSET)

    return linear, angular

######################################################################

def wheel_lr_from_linear_angular(linear_angular):

    linear, angular = linear_angular

    l = linear - angular*ROBOT_WHEEL_OFFSET
    r = linear + angular*ROBOT_WHEEL_OFFSET

    return numpy.array([l, r])

######################################################################

def clamp_abs(quantity, limit):
    return numpy.clip(quantity, -limit, limit)
    
######################################################################

def iir_filter(meas, inputs, outputs, do_filter, B, A):
    
    assert len(inputs) == len(B)
    assert len(outputs) == len(A)

    inputs[1:] = inputs[:-1]
    inputs[0] = meas

    if do_filter:
        output = numpy.dot(B, inputs) - numpy.dot(A, outputs)
    else:
        output = meas

    outputs[1:] = outputs[:-1]
    outputs[0] = output

    return output

######################################################################

class Robot(SimObject):

    def __init__(self, world):

        super().__init__(world=world)

        self.body = None

        # left and then right
        self.wheel_vel_cmd = numpy.array([0, 0], dtype=float)

        self.wheel_offsets = numpy.array([
            [ ROBOT_WHEEL_OFFSET, 0],
            [-ROBOT_WHEEL_OFFSET, 0]
        ], dtype=float)
        

        self.odom_linear_angular_vel = numpy.zeros(2, dtype=numpy.float32)
        
        self.odom_wheel_vel = numpy.zeros(2, dtype=numpy.float32)
        
        self.odom_pose = Transform2D()
        self.initial_pose_inv = Transform2D()

        self.desired_linear_angular_vel = numpy.zeros(2, dtype=numpy.float64)
        
        self.desired_linear_angular_vel_raw = numpy.zeros((2, len(SETPOINT_FILTER_B)),
                                                          dtype=numpy.float64)
        
        self.desired_linear_angular_vel_filtered = numpy.zeros((2, len(SETPOINT_FILTER_A)),
                                                               dtype=numpy.float64)
        
        self.desired_wheel_vel = numpy.zeros(2, dtype=numpy.float32)
        self.wheel_stopped_count = numpy.zeros(2, dtype=int)

        self.wheel_vel_integrator = numpy.zeros(2, dtype=numpy.float32)
        self.wheel_vel = numpy.zeros(2, dtype=numpy.float32)

        # row 0: left speed/current, row 1: right speed/current
        self.motor_state = numpy.zeros((2, 2), dtype=numpy.float64)

        # torques for motor
        self.motor_torques = numpy.zeros(2)
        self.motor_voltages_raw = numpy.zeros((2, len(VOLTAGE_FILTER_B)))
        self.motor_voltages_filtered = numpy.zeros((2, len(VOLTAGE_FILTER_A)))
        self.wheel_forces = numpy.zeros(2)
        self.wheel_skid_forces = numpy.zeros(2)

        self.motor_model = Motor()

        self.forward_vel = 0.0

        self.rolling_mu = 0.15
        
        self.motors_enabled = True

        self.bump = numpy.zeros(len(BUMP_ANGLE_RANGES), dtype=numpy.uint8)

        self.leds_on = False

        self.log_vars = numpy.zeros(len(LOG_NAMES), dtype=numpy.float32)

        self.filter_setpoints = False
        self.filter_vel = True

        if 'URSIM_PERFECT_ODOMETRY' in os.environ:
            print('**********************************************************************')
            print('URSIM_PERFECT_ODOMETRY was set, using perfect odometry!')
            print('**********************************************************************')
            print()
            self.perfect_odometry = True
        else:
            self.perfect_odometry = False

        if 'URSIM_PERFECT_CONTACT' in os.environ:
            print('**********************************************************************')
            print('URSIM_PERFECT_CONTACT was set, disabling perturbation forces!')
            print('**********************************************************************')
            print()
            self.perfect_contact = True
        else:
            self.perfect_contact = False

        self.initialize()

    def initialize(self, position=None, angle=None):

        self.destroy()

        if position is None:
            position = (0.0, 0.0)

        if angle is None:
            angle = 0.0

        self.colliders = set()

        self.bump[:] = 0
        
        self.orig_position = position
        self.orig_angle = angle

        self.odom_pose = Transform2D()
        self.initial_pose_inv = Transform2D(position, angle).inverse()

        self.odom_tick = 0

        self.forward_vel = 0.0

        self.desired_linear_angular_vel[:] = 0
        self.desired_linear_angular_vel_raw[:] = 0
        self.desired_linear_angular_vel_filtered[:] = 0

        self.odom_wheel_vel[:] = 0
        self.wheel_stopped_count[:] = 0
        self.wheel_vel_integrator[:] = 0
        self.wheel_vel[:] = 0
        self.motor_state[:] = 0
        self.motor_torques[:] = 0
        self.motor_voltages_raw[:] = 0
        self.motor_voltages_filtered[:] = 0
        self.wheel_forces[:] = 0
        self.wheel_skid_forces[:] = 0

        self.body = self.world.CreateDynamicBody(
            position = b2ple(position),
            angle = float(angle),
            fixtures = B2D.b2FixtureDef(
                shape = B2D.b2CircleShape(radius=ROBOT_BASE_RADIUS),
                density = 1.0,
                restitution = 0.25,
                friction = 0.1,
            ),
            userData = self
        )

        self.body.massData = B2D.b2MassData(
            mass = ROBOT_BASE_MASS,
            I = ROBOT_BASE_I
        )

        ##################################################

        self.gfx_objects.append(
            gfx.IndexedPrimitives.cylinder(
                ROBOT_BASE_RADIUS, ROBOT_BASE_HEIGHT, 64, 1,
                ROBOT_BASE_COLOR,
                pre_transform=gfx.tz(0.5*ROBOT_BASE_HEIGHT + ROBOT_BASE_Z),
                specular_exponent=40.0,
                specular_strength=0.75
            )
        )

        tx = -0.5*ROBOT_CAMERA_DIMS[0]
        
        self.gfx_objects.append(
            gfx.IndexedPrimitives.box(
                ROBOT_CAMERA_DIMS,
                ROBOT_BASE_COLOR,
                pre_transform=gfx.translation_matrix(
                    gfx.vec3(tx, 0, ROBOT_CAMERA_LENS_Z)),
                specular_exponent=40.0,
                specular_strength=0.75
            )
        )

        btop = ROBOT_BASE_Z + ROBOT_BASE_HEIGHT
        cbottom = ROBOT_CAMERA_BOTTOM_Z

        pheight = cbottom - btop

        for y in [-0.1, 0.1]:

            self.gfx_objects.append(
                gfx.IndexedPrimitives.cylinder(
                    0.01, pheight, 32, 1,
                    gfx.vec3(0.75, 0.75, 0.75),
                    pre_transform=gfx.translation_matrix(gfx.vec3(tx, y, 0.5*pheight + btop)),
                    specular_exponent=20.0,
                    specular_strength=0.75
                )
            )

            
        vdata = numpy.zeros((8, 3), dtype=numpy.float32)
        xy = vdata[:, :2]
        vdata[:, 2] = btop + 0.001

        a = 0.08
        b = 0.04
        c = -0.15
        d = 0.025
        cd = -0.11
        e = 0.105

        xy[0] = (c, b)
        xy[1] = (cd, 0)
        xy[2] = (c, -b)
        xy[3] = (d, a)
        xy[4] = (d, b)
        xy[5] = (d, -b)
        xy[6] = (d, -a)
        xy[7] = (e, 0)

        indices = [ [ 0, 1, 4 ],
                    [ 1, 5, 4 ],
                    [ 2, 5, 1 ],
                    [ 3, 4, 7 ],
                    [ 4, 5, 7 ],
                    [ 5, 6, 7 ] ]

        indices = numpy.array(indices, dtype=numpy.uint8)
        
        arrow = gfx.IndexedPrimitives.faceted_triangles(
            vdata, indices, gfx.vec3(0.8, 0.7, 0.0),
            specular_exponent=40.0,
            specular_strength=0.75
        )

        self.gfx_objects.append(arrow)

        self.bump_lites = []

        for theta_deg in [ 45, 0, -45 ]:

            theta_rad = theta_deg*numpy.pi/180
            r = 0.14
            tx = r*numpy.cos(theta_rad)
            ty = r*numpy.sin(theta_rad)

            lite = gfx.IndexedPrimitives.sphere(
                0.011, 16, 12,
                gfx.vec3(0.25, 0, 0),
                pre_transform=gfx.translation_matrix(gfx.vec3(tx, ty, btop)),
                specular_exponent=50.0,
                specular_strength=0.25,
                enable_lighting=True)

            self.gfx_objects.append(lite)
            self.bump_lites.append(lite)
        

    def reset(self):
        self.initialize(self.orig_position, self.orig_angle)

    def setup_log(self, datalog):
        datalog.add_variables(LOG_NAMES, self.log_vars)

    def update_log(self):

        l = self.log_vars

        rel_odom = self.initial_pose_inv * Transform2D(self.body.position,
                                                       self.body.angle)
        
        l[LOG_ROBOT_POS_X] = rel_odom.position[0]
        l[LOG_ROBOT_POS_Y] = rel_odom.position[1]
        l[LOG_ROBOT_POS_ANGLE] = rel_odom.angle
        l[LOG_ROBOT_VEL_ANGLE] = self.body.angularVelocity
        l[LOG_ROBOT_CMD_VEL_FORWARD] = self.desired_linear_angular_vel[0]
        l[LOG_ROBOT_CMD_VEL_ANGULAR] = self.desired_linear_angular_vel[1]
        l[LOG_ROBOT_CMD_VEL_LWHEEL] = self.desired_wheel_vel[0]
        l[LOG_ROBOT_CMD_VEL_RWHEEL] = self.desired_wheel_vel[1]
        l[LOG_ROBOT_VEL_FORWARD] = self.forward_vel
        l[LOG_ROBOT_VEL_LWHEEL] = self.wheel_vel[0]
        l[LOG_ROBOT_VEL_RWHEEL] = self.wheel_vel[1]
        l[LOG_ROBOT_BUMP_LEFT:LOG_ROBOT_BUMP_LEFT+3] = self.bump

        l[LOG_ODOM_POS_X] = self.odom_pose.position[0]
        l[LOG_ODOM_POS_Y] = self.odom_pose.position[1]
        l[LOG_ODOM_POS_ANGLE] = self.odom_pose.angle
        l[LOG_ODOM_VEL_LWHEEL] = self.odom_wheel_vel[0]
        l[LOG_ODOM_VEL_RWHEEL] = self.odom_wheel_vel[1]
        l[LOG_ODOM_VEL_FORWARD] = self.odom_linear_angular_vel[0]
        l[LOG_ODOM_VEL_ANGLE] = self.odom_linear_angular_vel[1]

        l[LOG_MOTOR_VEL_L] = self.motor_state[0, 0]
        l[LOG_MOTOR_VEL_R] = self.motor_state[1, 0]
        l[LOG_MOTOR_CURRENT_L] = self.motor_state[0, 1]
        l[LOG_MOTOR_CURRENT_R] = self.motor_state[1, 1]

        l[LOG_MOTOR_VOLTAGE_L] = self.motor_voltages_filtered[0,0]
        l[LOG_MOTOR_VOLTAGE_R] = self.motor_voltages_filtered[1,0]
        l[LOG_MOTOR_TORQUE_L] = -self.motor_torques[0]
        l[LOG_MOTOR_TORQUE_R] = -self.motor_torques[1]
        l[LOG_WHEEL_FORCE_L] = self.wheel_forces[0]
        l[LOG_WHEEL_FORCE_R] = self.wheel_forces[1]
        l[LOG_WHEEL_SKID_FORCE_L] = self.wheel_skid_forces[0]
        l[LOG_WHEEL_SKID_FORCE_R] = self.wheel_skid_forces[1]

        l[LOG_MOTORS_ENABLED] = self.motors_enabled

    def sim_update(self, time, dt):

        dt_sec = dt.total_seconds()

        body = self.body

        current_tangent = body.GetWorldVector((1, 0))
        current_normal = body.GetWorldVector((0, 1))

        self.forward_vel = body.linearVelocity.dot(current_tangent)

        lateral_vel = body.linearVelocity.dot(current_normal)

        lateral_impulse = clamp_abs(-body.mass * lateral_vel,
                                    WHEEL_MAX_LATERAL_IMPULSE)

        body.ApplyLinearImpulse(lateral_impulse * current_normal,
                                body.position, True)
        
        for idx in range(2):
            iir_filter(self.desired_linear_angular_vel[idx],
                       self.desired_linear_angular_vel_raw[idx],
                       self.desired_linear_angular_vel_filtered[idx],
                       self.filter_setpoints, SETPOINT_FILTER_B, SETPOINT_FILTER_A)

        self.desired_wheel_vel = wheel_lr_from_linear_angular(
            self.desired_linear_angular_vel_filtered[:, 0]
        )

        if self.perfect_odometry:
            wheel_vel_noise = numpy.zeros(2)
        else:
            wheel_vel_noise = numpy.random.normal(size=2, scale=ODOM_NOISE_STDDEV)

        if self.perfect_contact:
            wheel_force_noise = numpy.zeros(2)
        else:
            wheel_force_noise = numpy.random.normal(size=2, scale=WHEEL_FORCE_MAX_STDDEV)

        mm = self.motor_model

        
        for idx, side in enumerate([1.0, -1.0]):

            offset = B2D.b2Vec2(0, side * ROBOT_WHEEL_OFFSET)

            world_point = body.GetWorldPoint(offset)
            
            ######################################################################
            # step 1: drive motor

            wheel_tgt_speed = mm.wheel_tgt_speed_from_motor_speed(
                self.motor_state[idx,0])

            self.wheel_vel[idx] = wheel_tgt_speed

            if wheel_tgt_speed > ODOM_NOISE_THRESHOLD_VEL:
                self.odom_wheel_vel[idx] = wheel_tgt_speed + wheel_vel_noise[idx]
            else:
                self.odom_wheel_vel[idx] = wheel_tgt_speed

            wheel_vel_error = (self.desired_wheel_vel[idx] -
                               self.odom_wheel_vel[idx])

            if (self.desired_wheel_vel[idx] == 0 and
                numpy.abs(self.odom_wheel_vel[idx]) < WHEEL_STOPPED_THRESHOLD_VEL):
                
                self.wheel_stopped_count[idx] += 1

            else:
                
                self.wheel_stopped_count[idx] = 0

            
            vel_int = self.wheel_vel_integrator[idx] + wheel_vel_error * dt_sec
            vel_int = clamp_abs(vel_int, MOTOR_VEL_INT_MAX)
            self.wheel_vel_integrator[idx] = vel_int

            if self.motors_enabled:

                if self.wheel_stopped_count[idx] > 5:
                    V_cmd = 0
                else:
                    V_cmd = MOTOR_VEL_KP*wheel_vel_error + MOTOR_VEL_KI * vel_int
                    
                V_cmd = clamp_abs(V_cmd, mm.V_nominal)

            else:

                V_cmd = 0

            filter_motors = True
            
            iir_filter(V_cmd,
                       self.motor_voltages_raw[idx],
                       self.motor_voltages_filtered[idx],
                       filter_motors,
                       VOLTAGE_FILTER_B, VOLTAGE_FILTER_A)

            motor_torque = self.motor_torques[idx]

            V_cmd_filt = self.motor_voltages_filtered[idx, 0]

            motor_control = numpy.array([motor_torque, V_cmd_filt])

            self.motor_state[idx] = mm.simulate_dynamics(self.motor_state[idx],
                                                         motor_control,
                                                         dt_sec)
            
            ######################################################################
            # step 2: tie to world physics

            wheel_tgt_speed = mm.wheel_tgt_speed_from_motor_speed(
                self.motor_state[idx,0])

            robot_vel_at_wheel = body.GetLinearVelocityFromWorldPoint(world_point)
            robot_fwd_vel_at_wheel = robot_vel_at_wheel.dot(current_tangent)

            vel_mismatch = wheel_tgt_speed - robot_fwd_vel_at_wheel

            # note 0.5 because we have two wheels
            vel_impulse = 0.5 * vel_mismatch * self.body.mass

            F_max = numpy.maximum(0, WHEEL_FORCE_MAX + wheel_force_noise[idx])

            F = vel_impulse / dt_sec
            Fclamp = clamp_abs(F, F_max)

            self.wheel_skid_forces[idx] = Fclamp - F
            self.wheel_forces[idx] = F
            self.motor_torques[idx] = mm.motor_torque_from_wheel_tgt_force(-F)

            body.ApplyForce(F * current_tangent,
                            world_point, True)

        ##################################################

        self.odom_linear_angular_vel[:] = linear_angular_from_wheel_lr(
            self.odom_wheel_vel)
        
        self.odom_tick += 1

        if self.perfect_odometry:

            T_world_from_orig = Transform2D(self.orig_position, self.orig_angle)
            T_world_from_cur = Transform2D(self.body.position, self.body.angle)

            T_orig_from_cur = T_world_from_orig.inverse() * T_world_from_cur

            self.odom_pose.position = T_orig_from_cur.position
            self.odom_pose.angle = T_orig_from_cur.angle
        
        elif self.odom_tick % ODOM_FREQUENCY == 0:

            odt = dt_sec * ODOM_FREQUENCY
            odom_fwd = odt * self.odom_linear_angular_vel[0]
            odom_spin = odt * self.odom_linear_angular_vel[1]

            self.odom_pose.position += odom_fwd * self.odom_pose.matrix[:2, 0]
            self.odom_pose.angle += odom_spin

        ##################################################
        
        self.bump[:] = 0

        transformA = self.body.transform

        finished_colliders = set()

        for collider in self.colliders:
            
            transformB = collider.body.transform

            collider_did_hit = False
            
            for fixtureA in self.body.fixtures:
                shapeA = fixtureA.shape

                for fixtureB in collider.body.fixtures:
                    shapeB = fixtureB.shape

                    pointA, _, distance, _ = B2D.b2Distance(
                        shapeA = shapeA,
                        shapeB = shapeB,
                        transformA = transformA,
                        transformB = transformB
                    )

                    if distance < BUMP_DIST:

                        collider_did_hit = True

                        lx, ly = self.body.GetLocalPoint(pointA)

                        theta = numpy.arctan2(ly, lx)

                        in_range = ( (theta >= BUMP_ANGLE_RANGES[:,0]) &
                                     (theta <= BUMP_ANGLE_RANGES[:,1]) )

                        self.bump |= in_range
                        
            if not collider_did_hit:
                finished_colliders.add(collider)

        #print('bump:', self.bump)
        self.colliders -= finished_colliders

    def render(self):

        for i in range(3):
            lite = self.bump_lites[i]
            bump = self.bump[i]
            if bump or self.leds_on:
                lite.enable_lighting = False
                lite.color = gfx.vec3(1, 0, 0)
            else:
                lite.enable_lighting = True
                lite.color = gfx.vec3(0.25, 0, 0)
        
        super().render()
        
        
                                
######################################################################

class SvgTransformer:

    def __init__(self, width, height, scl):

        self.scl = scl
        self.dims = numpy.array([width, height], dtype=numpy.float32) * scl

        shift = numpy.array([[1, 0, 0],
                             [0, 1, self.dims[1]],
                             [0, 0, 1]])
        
        flip = numpy.array([[1, 0, 0],
                            [0, -1, 0],
                            [0, 0, 1]])

        S = numpy.array([[scl, 0, 0],
                         [0, scl, 0],
                         [0, 0, 1]])

        self.global_transform = numpy.dot(numpy.dot(shift, flip), S)
        

        self.local_transform = numpy.eye(3)

    def set_local_transform(self, xx, yx, xy, yy, x0, y0):

        self.local_transform = numpy.array([[xx, xy, x0],
                                            [yx, yy, y0],
                                            [0, 0, 1]])

    def transform(self, x, y):

        point = numpy.array([x, y, 1])
        point = numpy.dot(self.local_transform, point)
        point = numpy.dot(self.global_transform, point)

        return point[:2].astype(numpy.float32)

    def scale_dims(self, x, y):
        return self.scl * x, self.scl*y

######################################################################
# helper function for below

def _flatten(seg, scl, u0, p0, u1, p1, points):

    # precondition: points[-1] = p0 unless very first point

    d01 = svgelements.Point.distance(p0, p1)

    if d01*scl > TAPE_DASH_SIZE:

        umid = 0.5*(u0 + u1)
        pmid = seg.point(umid)

        _flatten(seg, scl, u0, p0, umid, pmid, points)

        # now pmid is added

        _flatten(seg, scl, umid, pmid, u1, p1, points)

        # now p1 is added

    else:

        points.append(p1)

    # postcondition: points[-1] = p1

######################################################################
# flatten a bezier path segment
    
def flatten(seg, scl):
    
    p0 = seg.point(0)
    p1 = seg.point(1)

    points = []
    
    _flatten(seg, scl, 0.0, p0, 1.0, p1, points)

    return points

######################################################################
# get position and angle from triangle

def robot_from_triangle(points):

    assert len(points) == 3

    pairs = numpy.array([
        [0, 1],
        [1, 2],
        [2, 0]
    ])

    diffs = points[pairs[:,0]] - points[pairs[:,1]]

    dists = numpy.linalg.norm(diffs, axis=1)
    a = dists.argmin()

    i, j = pairs[a]
    k = 3-i-j

    tangent = diffs[a]
    ctr = 0.5*(points[i] + points[j])

    normal = gfx.normalize(gfx.vec2(-tangent[1], tangent[0]))

    dist = numpy.dot(normal, points[k]-ctr)

    if dist < 0:
        normal = -normal
        dist = -dist

    robot_init_position = ctr + 0.5 * dist * normal
    robot_init_angle = numpy.arctan2(normal[1], normal[0])

    return robot_init_position, robot_init_angle

######################################################################

class SimObserver:

    """Base class for objects that can get notified when simulator updates
    happen, and are given access to the simulator state. Good for
    making scorekeepers for various objectives..."""

    def __init__(self):
        """Initializer."""
        pass

    def register(self, sim):
        """Called once when observer is added to simulator. The simulation
        environment should be set up but the app not yet started at
        this point."""
        pass

    def initialize(self, sim):
        """Called before first update and after any restarts."""
        pass

    def pre_update(self, sim):
        """Called before each update (but after logging has started)."""
        pass

    def post_update(self, sim):
        """Called after each update (but before log row is written)."""
        pass

######################################################################

class RoboSim(B2D.b2ContactListener):

    def __init__(self):

        super().__init__()

        self.world = B2D.b2World(gravity=(0, 0), doSleep=True)
        self.world.contactListener = self

        self.dims = numpy.array([-1, -1], dtype=numpy.float32)

        self.robot = Robot(self.world)

        self.room = Room(self.world, [4.0, 4.0])

        self.modification_counter = 0

        self.tape_strips = dict()
        
        self.objects = [ self.robot, self.room ]

        self.dt = timedelta(milliseconds=10)
        
        self.physics_ticks_per_update = 4

        self.datalog = DataLog(self.dt * self.physics_ticks_per_update)
        self.robot.setup_log(self.datalog)

        self.velocity_iterations = 6
        self.position_iterations = 2
        
        self.sim_time = timedelta()
        self.sim_ticks = 0

        self.svg_file = None

        self.observers = []

        print('created the world!')

    def set_dims(self, room_width, room_height):
        self.dims = numpy.array([room_width, room_height],
                                dtype=numpy.float32)
        self.room.initialize(self.dims)
        self.svg_file = None
        self.modification_counter += 1

    def add_object(self, obj):
        self.objects.append(obj)
        self.svg_file = None
        self.modification_counter += 1
        return obj

    def add_box(self, dims, pctr, theta):
        self.add_object(Box(self.world, dims, pctr, theta))

    def add_pylon(self, position, cname):
        self.add_object(Pylon(self.world, position, cname))

    def add_pylon(self, position, cname):
        self.add_object(Pylon(self.world, position, cname))

    def add_ball(self, position):
        self.add_object(Ball(self.world, position))

    def add_tape_strip(self, points, cname):
        if cname not in self.tape_strips:
            self.tape_strips[cname] = self.add_object(TapeStrips([points], cname))
        else:
            self.tape_strips[cname].point_lists.append(points)
            self.modification_counter += 1

    def add_wall(self, p0, p1):
        self.add_object(Wall(self.world, numpy.array(p0), numpy.array(p1)))

    def add_observer(self, observer):
        self.observers.append(observer)
        observer.register(self)
        observer.initialize(self)

    def reset(self, reload_svg=True):
        
        filename = self.datalog.finish()
        if filename is not None:
            print('wrote log', filename)
            
        if reload_svg and self.svg_file is not None:
            self.clear()
            if not isinstance(self.svg_file, str):
                self.svg_file.seek(0)
            self.load_svg(self.svg_file)
        else:
            self.sim_time = timedelta(0)
            self.sim_ticks = 0
            for obj in self.objects:
                obj.reset()
        self.modification_counter += 1

        for observer in self.observers:
            observer.initialize(self)

    def clear(self):

        filename = self.datalog.finish()
        if filename is not None:
            print('wrote log', filename)
        
        self.sim_time = timedelta(0)
        self.sim_ticks = 0
        self.modification_counter += 1

        assert self.robot == self.objects[0]

        for obj in self.objects[2:]:
            obj.destroy()

        self.tape_strips = dict()
            
        self.objects[:] = [self.robot, self.room]

    def load_svg(self, svgfile):

        svg = svgelements.SVG.parse(svgfile, color='none')
        print('parsed', svgfile)

        scl = 1e-2

        xform = SvgTransformer(svg.viewbox.viewbox_width,
                               svg.viewbox.viewbox_height, scl)

        self.set_dims(*xform.dims)

        robot_init_position = 0.5*self.dims
        robot_init_angle = 0.0

        tape_point_lists = []

        items = [ item for item in svg ]

        while len(items):

            item = items.pop(0)

            if isinstance(item, svgelements.Group):
                items = [ child for child in item ] + items
                continue
            
            # any geometry we want to deal with has an xform
            if not hasattr(item, 'transform'):
                continue

            xx, yx, xy, yy, x0, y0 = [getattr(item.transform, letter)
                                      for letter in 'abcdef']

            det = xx*yy - yx*xy
            is_rigid = (abs(det - 1) < 1e-4)
            
            assert(is_rigid)

            xform.set_local_transform(xx, yx, xy, yy, x0, y0)
            
            fcolor = None
            scolor = None

            if item.fill.value is not None:
                fcolor = vec_from_svg_color(item.fill)

            if item.stroke.value is not None:
                scolor = vec_from_svg_color(item.stroke)

            points = None
            is_closed = False

            if isinstance(item, svgelements.Rect):

                w, h = xform.scale_dims(item.width, item.height)

                cx = item.x + 0.5*item.width
                cy = item.y + 0.5*item.height

                dims = gfx.vec3(w, h, min(w, h))
                pctr = xform.transform(cx, cy)
                pfwd = xform.transform(cx+1, cy)
                delta = pfwd-pctr
                theta = numpy.arctan2(delta[1], delta[0])
                
                if numpy.all(fcolor == 1):

                    # room rectangle
                    pass

                else:

                    self.add_box(dims, pctr, theta)
                
            elif (isinstance(item, svgelements.Circle) or
                  isinstance(item, svgelements.Ellipse)):
                
                cidx, color = match_svg_color(fcolor, CIRCLE_COLORS)

                position = xform.transform(item.cx, item.cy)

                if cidx == 0:
                    self.add_ball(position)
                else:
                    self.add_pylon(position,
                                   PYLON_COLOR_NAMES[cidx-1])
                                        
            elif isinstance(item, svgelements.SimpleLine):

                p0 = xform.transform(item.x1, item.y1)
                p1 = xform.transform(item.x2, item.y2)

                points = numpy.array([p0, p1])
                is_closed = False

            elif isinstance(item, svgelements.Polyline):
                
                points = numpy.array(
                    [xform.transform(p.x, p.y) for p in item.points])

                is_closed = False

            elif isinstance(item, svgelements.Path):

                points = []
                
                for seg in item.segments():
                    if isinstance(seg, svgelements.Move):
                        points.append(seg.point(0))
                    elif isinstance(seg, svgelements.Line):
                        points.append(seg.point(1))
                    elif isinstance(seg, svgelements.Close):
                        is_closed = True
                    else:
                        points.extend(flatten(seg, scl))

                points = numpy.array([ xform.transform(p.x, p.y) for p in points ])
                
            elif isinstance(item, svgelements.Polygon):

                points = numpy.array(
                    [xform.transform(p.x, p.y) for p in item.points])

                is_closed = True

            else:
                
                print('*** warning: ignoring SVG item:', item, '***')
                continue

            ##################################################

            if points is not None:

                if len(points) == 2 and not is_closed:

                    cidx, color = match_svg_color(scolor, LINE_COLORS)

                    if cidx < len(TAPE_COLORS):
                        self.add_tape_strip(points, TAPE_COLOR_NAMES[cidx])
                    else:
                        self.add_wall(points[0], points[1])

                elif len(points) == 3 and is_closed:

                    robot_init_position, robot_init_angle = robot_from_triangle(points)

                else:

                    if is_closed:
                        points = numpy.vstack((points, [points[0]]))

                    cidx, color = match_svg_color(scolor, TAPE_COLORS)
                    self.add_tape_strip(points, TAPE_COLOR_NAMES[cidx])

            ##################################################

        assert self.robot == self.objects[0]
        assert self.room == self.objects[1]
        
        self.initialize_robot(robot_init_position,
                              robot_init_angle)

        self.svg_file = svgfile

    def initialize_robot(self, pos, angle):
        self.robot.initialize(pos, angle)

    def update(self):

        if not self.datalog.is_logging():
            filename = self.datalog.begin_log()
            print('starting log', filename)

        for observer in self.observers:
            observer.pre_update(self)
        
        for i in range(self.physics_ticks_per_update):

            for obj in self.objects:
                obj.sim_update(self.sim_time, self.dt)

            self.world.Step(self.dt.total_seconds(),
                            self.velocity_iterations,
                            self.position_iterations)

            self.world.ClearForces()

            self.sim_time += self.dt
            self.sim_ticks += 1

        self.robot.update_log()
        
        for observer in self.observers:
            observer.post_update(self)
        
        self.datalog.append_log_row()

    def kick_ball(self):

        for obj in self.objects:
            if isinstance(obj, Ball):
                kick_impulse = B2D.b2Vec2(1, 0)
                wdist = None
                for other in self.objects:
                    if isinstance(other, Robot):
                        diff = other.body.position - obj.body.position
                        dist = diff.length
                        if wdist is None or dist < wdist:
                            wdist = dist
                            desired_vel = diff * 4 / dist
                            actual_vel = obj.body.linearVelocity
                            kick_impulse = (desired_vel - actual_vel)*BALL_MASS
                obj.body.ApplyLinearImpulse(kick_impulse, obj.body.position, True)
                obj.body.bullet = True
                print('kicked the ball')
        
    def PreSolve(self, contact, old_manifold):

        other = None

        if contact.fixtureA.body == self.robot.body:
            other = contact.fixtureB.body
        elif contact.fixtureB.body == self.robot.body:
            other = contact.fixtureA.body

        if other is not None:
            self.robot.colliders.add(other.userData)
