######################################################################
#
# robosim_core.py
# 
# Written for ENGR 028/CPSC 082: Mobile Robotics, Summer 2020
# Copyright (C) Matt Zucker 2020
#
######################################################################

import numpy
import graphics as gfx
import Box2D as B2D
import svgelements as se
import os
import robosim_logging as rlog



TAPE_COLOR = gfx.vec3(0.3, 0.3, 0.9)

CARDBOARD_COLOR = gfx.vec3(0.8, 0.7, 0.6)

LINE_COLORS = [
    TAPE_COLOR,
    CARDBOARD_COLOR
]

PYLON_COLORS = [
    gfx.vec3(1.0, 0.5, 0),
    gfx.vec3(0, 0.8, 0),
]

BALL_COLOR = gfx.vec3(0.5, 0, 1)

CIRCLE_COLORS = [ BALL_COLOR ] + PYLON_COLORS

PYLON_RADIUS = 0.05
PYLON_HEIGHT = 0.20

PYLON_MASS = 0.250
PYLON_I = PYLON_MASS * PYLON_RADIUS * PYLON_RADIUS

BALL_RADIUS = 0.1

TAPE_RADIUS = 0.025

TAPE_DASH_SIZE = 0.15

TAPE_POLYGON_OFFSET = 0.001

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
ROBOT_BASE_MASS = 2.35
ROBOT_BASE_I = 0.5*ROBOT_BASE_MASS*ROBOT_BASE_RADIUS**2

ROBOT_BASE_COLOR = gfx.vec3(0.1, 0.1, 0.1)

ROBOT_CAMERA_DIMS = gfx.vec3(0.08, 0.25, 0.04)
ROBOT_CAMERA_Z = 0.18

ROBOT_WHEEL_OFFSET = 0.5*0.230
ROBOT_WHEEL_RADIUS = 0.035
ROBOT_WHEEL_WIDTH = 0.021

DEG = numpy.pi / 180

BUMP_ANGLE_RANGES = numpy.array([
    [ 20, 70 ],
    [ -25, 25 ],
    [ -70, -25 ]
], dtype=numpy.float32) * DEG

BUMP_DIST = 0.005

LOG_ROBOT_POS_X =           0
LOG_ROBOT_POS_Y =           1
LOG_ROBOT_POS_ANGLE =       2
LOG_ROBOT_VEL_X =           3
LOG_ROBOT_VEL_Y =           4
LOG_ROBOT_VEL_ANGLE =       5
LOG_ROBOT_CMD_VEL_FORWARD = 6
LOG_ROBOT_CMD_VEL_ANGULAR = 7
LOG_ROBOT_CMD_VEL_LWHEEL  = 8
LOG_ROBOT_CMD_VEL_RWHEEL  = 9
LOG_ROBOT_VEL_FORWARD =     10
LOG_ROBOT_VEL_LWHEEL =      11
LOG_ROBOT_VEL_RWHEEL =      12
LOG_ROBOT_MOTORS_ENABLED  = 13
LOG_ROBOT_BUMP_LEFT       = 14
LOG_ROBOT_BUMP_CENTER     = 15
LOG_ROBOT_BUMP_RIGHT      = 16

LOG_NUM_VARS        = 17


LOG_NAMES = [
    'robot.pos.x',
    'robot.pos.y',
    'robot.pos.angle',
    'robot.vel.x',
    'robot.vel.y',
    'robot.vel.angle',
    'robot.cmd_vel.forward',
    'robot.cmd_vel.angle',
    'robot.cmd_wheel_vel.l',
    'robot.cmd_wheel_vel.r',
    'robot.vel.forward',
    'robot.wheel_vel.l',
    'robot.wheel_vel.r',
    'robot.motors_enabled',
    'robot.bump.left',
    'robot.bump.center',
    'robot.bump.right',
]

assert len(LOG_NAMES) == LOG_NUM_VARS


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

class Transform2D:

    def __init__(self, *args):

        # args can be:
        # 3 scalars (x, y, theta)
        # a translation and rotation ((x, y), theta)
        # another Transform2D (makes a copy)
        # a Box2D transform object (makes a copy)

        self.position = numpy.empty(2, dtype=numpy.float32)
        self._angle = numpy.float32()

        if len(args) == 3:
            self.position[:] = args[:2]
            self._angle = args[2]
        elif len(args) == 2:
            self.position[:] = args[0]
            self._angle = args[1]
        elif len(args) == 1:
            self.position[:] = args[0].position
            self._angle = args[0].angle
        
        self._matrix = numpy.zeros((3, 3), dtype=numpy.float32)

    def rotation_matrix(self):
        return self.matrix[:2,:2]

    @property
    def matrix(self):
        if self._matrix[2,2] != 1:
            x, y = self.position
            c = numpy.cos(self._angle)
            s = numpy.sin(self._angle)
            self._matrix[:] = [[c, -s, x], [s, c, y], [0, 0, 1]]
        return self._matrix

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        self._angle = angle
        self._matrix[2,2] = 0

    def transform_fwd(self, other):

        R2 = self.rotation_matrix()
        t2 = self.position
        
        if isinstance(other, self.__class__):
            
            t1 = other.position
            
            return self.__class__(numpy.dot(R2, t1) + t2,
                                  self.angle + other.angle)

        else:
            
            return numpy.dot(R2, other) + t2


    def transform_inv(self, other):

        R2inv = self.rotation_matrix().T
        t2 = self.position

        if isinstance(other, self.__class__):

            t1 = other.position

            return self.__class__(numpy.dot(R2inv, t1 - t2),
                                  other.angle - self.angle)

        else:

            return numpy.dot(R2inv, other - t2)

    def inverse(self):

        R2inv = self.rotation_matrix().T
        pinv = numpy.dot(R2inv, -self.position)

        return self.__class__(pinv, -self.angle)

    def __mul__(self, other):

        return self.transform_fwd(other)

    def __str__(self):
        return repr(self)

    def __repr__(self):
        return 'Transform2D(({}, {}), {})'.format(
            repr(self.position[0]), repr(self.position[1]),
            repr(self._angle))
    

######################################################################

class SimObject:

    def __init__(self):
        
        self.gfx_objects = []
        
        self.body = None
        self.body_linear_mu = None
        self.body_angular_mu = None

    def sim_update(self, world, time, dt):

        if self.body_linear_mu is not None:
            self.body.ApplyForceToCenter(
                -self.body_linear_mu * self.body.linearVelocity,
                True)

        if self.body_angular_mu is not None:
            self.body.ApplyTorque(
                -self.body_angular_mu * self.body.angularVelocity,
                True)

######################################################################                
                
class Pylon(SimObject):

    static_gfx_object = None

    def __init__(self, world, position, color, material_id):

        super().__init__()
        
        assert position.shape == (2,) and position.dtype == numpy.float32
        assert color.shape == (3,) and color.dtype == numpy.float32

        self.body = world.CreateDynamicBody(
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

        self.body_linear_mu = 0.9 * PYLON_MASS * 10.0

        self.color = color

        self.material_id = material_id

######################################################################

class Ball(SimObject):

    static_gfx_object = None

    def __init__(self, world, position):

        super().__init__()
        
        assert position.shape == (2,) and position.dtype == numpy.float32

        self.body = world.CreateDynamicBody(
            position = b2ple(position),
            fixtures = B2D.b2FixtureDef(
                shape = B2D.b2CircleShape(radius=BALL_RADIUS),
                density = BALL_DENSITY,
                restitution = 0.98,
                friction = 0.95
            ),
            userData = self
        )

        self.body_linear_mu = 0.01 * BALL_MASS * 10.0
        
        
######################################################################

class Wall(SimObject):

    def __init__(self, world, p0, p1):

        super().__init__()
        
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
            B2D.b2PolygonShape(box=(b2ple(0.5*dims[:2]))),
            B2D.b2PolygonShape(box=(r, r, (bx, 0), 0)),
            B2D.b2PolygonShape(box=(r, r, (-bx, 0), 0)),
        ]
            
        self.body = world.CreateDynamicBody(
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

        self.body_linear_mu = 0.9 * mass * 10.0
        self.body_angular_mu = I * 10.0
        
        self.body.massData = B2D.b2MassData(
            mass = mass,
            I = I
        )

        self.bx = bx
        self.dims = dims

        

######################################################################

class Box(SimObject):

    def __init__(self, world, dims, position, angle):

        super().__init__()
        
        assert dims.shape == (3,) and dims.dtype == numpy.float32
        assert position.shape == (2,) and position.dtype == numpy.float32

        self.body = world.CreateDynamicBody(
            position = b2ple(position),
            angle = float(angle),
            fixtures = B2D.b2FixtureDef(
                shape = B2D.b2PolygonShape(box=(b2ple(0.5*dims[:2]))),
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

        self.body_linear_mu = 0.9 * mass * 10.0
        self.body_angular_mu = I * 10.0
        
        self.body.massData = B2D.b2MassData(
            mass = mass,
            I = I
        )

        self.dims = dims

######################################################################

class Room(SimObject):

    def __init__(self, world, dims):

        super().__init__()
        
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
        
        self.body = world.CreateStaticBody(
            userData = self,
            shapes = shapes
        )


######################################################################

class TapeStrips(SimObject):

    def __init__(self, point_lists):

        super().__init__()

        self.point_lists = point_lists

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

class Robot(SimObject):

    def __init__(self, world):

        super().__init__()

        self.world = world
        self.body = None
        self.initialize()

        # left and then right
        self.wheel_vel_cmd = numpy.array([0, 0], dtype=float)

        self.wheel_offsets = numpy.array([
            [ ROBOT_WHEEL_OFFSET, 0],
            [-ROBOT_WHEEL_OFFSET, 0]
        ], dtype=float)
        
        self.max_lateral_impulse = 0.05 # m/(s*kg)
        self.max_forward_impulse = 0.05 # m/(s*kg)

        self.wheel_velocity_fitler_accel = 2.0 # m/s^2

        self.desired_linear_angular_velocity = numpy.zeros(2, dtype=numpy.float32)
        self.desired_wheel_velocity = numpy.zeros(2, dtype=numpy.float32)
        self.desired_wheel_velocity_filtered = numpy.zeros(2, dtype=numpy.float32)

        self.wheel_velocity = numpy.zeros(2, dtype=numpy.float32)

        self.forward_velocity = 0.0

        self.rolling_mu = 4.0
        
        self.motors_enabled = True

        self.bump = numpy.zeros(len(BUMP_ANGLE_RANGES), dtype=numpy.uint8)

        self.colliders = set()

        self.log_vars = numpy.zeros(LOG_NUM_VARS, dtype=numpy.float32)

    def initialize(self, position=None, angle=None):

        if self.body is not None:
            self.world.DestroyBody(self.body)
            self.body = None

        if position is None:
            position = (0.0, 0.0)

        if angle is None:
            angle = 0.0

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

    def setup_log(self, logger):
        logger.add_variables(LOG_NAMES, self.log_vars)

    def update_log(self):

        l = self.log_vars

        l[LOG_ROBOT_POS_X] = self.body.position.x
        l[LOG_ROBOT_POS_Y] = self.body.position.y
        l[LOG_ROBOT_POS_ANGLE] = self.body.angle
        l[LOG_ROBOT_VEL_X] = self.body.linearVelocity.x
        l[LOG_ROBOT_VEL_Y] = self.body.linearVelocity.y
        l[LOG_ROBOT_VEL_ANGLE] = self.body.angularVelocity
        l[LOG_ROBOT_CMD_VEL_FORWARD] = self.desired_linear_angular_velocity[0]
        l[LOG_ROBOT_CMD_VEL_ANGULAR] = self.desired_linear_angular_velocity[1]
        l[LOG_ROBOT_CMD_VEL_LWHEEL] = self.desired_wheel_velocity[0]
        l[LOG_ROBOT_CMD_VEL_RWHEEL] = self.desired_wheel_velocity[1]
        l[LOG_ROBOT_VEL_FORWARD] = self.forward_velocity
        l[LOG_ROBOT_VEL_LWHEEL] = self.wheel_velocity[0]
        l[LOG_ROBOT_VEL_RWHEEL] = self.wheel_velocity[1]
        l[LOG_ROBOT_MOTORS_ENABLED] = self.motors_enabled
        l[LOG_ROBOT_BUMP_LEFT:LOG_ROBOT_BUMP_LEFT+3] = self.bump

    def sim_update(self, world, time, dt):

        body = self.body

        current_tangent = body.GetWorldVector((1, 0))
        current_normal = body.GetWorldVector((0, 1))

        self.forward_velocity = body.linearVelocity.dot(current_tangent)

        lateral_velocity = body.linearVelocity.dot(current_normal)

        lateral_impulse = clamp_abs(-body.mass * lateral_velocity,
                                    self.max_lateral_impulse)

        body.ApplyLinearImpulse(lateral_impulse * current_normal,
                                body.position, True)

        self.desired_wheel_velocity = wheel_lr_from_linear_angular(
            self.desired_linear_angular_velocity
        )
        
        self.desired_wheel_velocity_filtered += clamp_abs(
            self.desired_wheel_velocity - self.desired_wheel_velocity_filtered,
            self.wheel_velocity_fitler_accel * dt)
        
        for idx, side in enumerate([1.0, -1.0]):

            offset = B2D.b2Vec2(0, side * ROBOT_WHEEL_OFFSET)

            world_point = body.GetWorldPoint(offset)

            wheel_velocity = body.GetLinearVelocityFromWorldPoint(world_point)

            wheel_fwd_velocity = wheel_velocity.dot(current_tangent)

            self.wheel_velocity[idx] = wheel_fwd_velocity
            
            if self.motors_enabled:

                wheel_velocity_error = (
                    self.desired_wheel_velocity_filtered[idx] - wheel_fwd_velocity
                )

                forward_impulse = clamp_abs(
                    wheel_velocity_error * body.mass,
                    self.max_forward_impulse)

                body.ApplyLinearImpulse(0.5 * forward_impulse * current_tangent,
                                        world_point, True)
                
            else:

                body.ApplyForce(-self.rolling_mu*wheel_fwd_velocity * current_tangent,
                                world_point, True)

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
    
class RoboSim(B2D.b2ContactListener):

    def __init__(self):

        super().__init__()

        self.world = B2D.b2World(gravity=(0, 0), doSleep=True)
        self.world.contactListener = self

        self.dims = numpy.array([-1, -1], dtype=numpy.float32)

        self.robot = Robot(self.world)
        self.objects = [ self.robot ]

        self.dt = 0.01 # 100 HZ
        self.physics_ticks_per_update = 4

        self.logger = rlog.Logger(self.dt)
        self.robot.setup_log(self.logger)

        self.velocity_iterations = 6
        self.position_iterations = 2
        
        self.remaining_sim_time = 0.0
        self.sim_time = 0.0
        self.sim_ticks = 0

        self.svg_filename = None

        self.framebuffer = None

        self.detections = None

        print('created the world!')

    def reload(self):

        self.logger.finish()

        self.clear()

        if self.svg_filename is not None:
            self.load_svg(self.svg_filename)

    def clear(self):

        self.remaining_sim_time = 0.0
        self.sim_time = 0.0
        self.sim_ticks = 0

        assert self.robot == self.objects[0]

        for obj in self.objects[1:]:
            if obj.body is not None:
                self.world.DestroyBody(obj.body)
            
        self.objects = [self.robot]
        

    def load_svg(self, svgfile):

        svg = se.SVG.parse(svgfile, color='none')
        print('parsed', svgfile)

        scl = 1e-2
        
        xform = SvgTransformer(svg.viewbox.viewbox_width,
                               svg.viewbox.viewbox_height, scl)
        
        self.dims = xform.dims

        self.objects.append(Room(self.world, self.dims))

        robot_init_position = 0.5*self.dims
        robot_init_angle = 0.0

        tape_point_lists = []

        for item in svg:

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

            if isinstance(item, se.Rect):

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
                    continue

                else:

                    self.objects.append( Box(self.world, dims,
                                             pctr, theta) )
                
            elif isinstance(item, se.Circle):
                
                cidx, color = match_svg_color(fcolor, CIRCLE_COLORS)

                position = xform.transform(item.cx, item.cy)

                if cidx == 0:
                    self.objects.append(Ball(self.world, position))
                else:
                    self.objects.append(Pylon(self.world, position,
                                              color, int(1 << cidx)))
                                        
            elif isinstance(item, se.SimpleLine):

                p0 = xform.transform(item.x1, item.y1)
                p1 = xform.transform(item.x2, item.y2)

                cidx, color = match_svg_color(scolor, LINE_COLORS)

                if cidx == 0:
                    
                    points = numpy.array([p0, p1])
                    tape_point_lists.append(points)
                    
                else:

                    self.objects.append( Wall(self.world, p0, p1) )
                
            elif isinstance(item, se.Polyline):
                
                points = numpy.array(
                    [xform.transform(p.x, p.y) for p in item.points])

                tape_point_lists.append(points)

            elif isinstance(item, se.Polygon):

                points = numpy.array(
                    [xform.transform(p.x, p.y) for p in item.points])

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

            else:
                
                print('*** warning: ignoring SVG item:', item, '***')
                continue

        if len(tape_point_lists):
            self.objects.append(TapeStrips(tape_point_lists))

        assert self.robot == self.objects[0]

        self.robot.initialize(robot_init_position,
                              robot_init_angle)
        

        self.svg_filename = os.path.abspath(svgfile)

    def update(self):

        for i in range(self.physics_ticks_per_update):

            for obj in self.objects:
                obj.sim_update(self.world, self.sim_time, self.dt)

            self.world.Step(self.dt,
                            self.velocity_iterations,
                            self.position_iterations)

            self.world.ClearForces()

            self.sim_time += self.dt
            self.sim_ticks += 1

        self.robot.update_log()
        self.logger.append_log_row()


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


def _test_load_environment():


    sim = RoboSim()
    sim.load_svg('environments/first_environment.svg')

    print('sim objects:')

    for sim_object in sim.objects:
        print('  ' + type(sim_object).__name__)
        if sim_object.body is not None:
            print('    transform:',
                  sim_object.body.position, sim_object.body.angle)
        
def _test_transform_2d():

    for attempt in range(100):

        x0, y0 = numpy.random.random(2)*2 - 1
        angle0 = (numpy.random.random()*2-1) * numpy.pi

        T0 = Transform2D(x0, y0, angle0)

        T0_alternatives = [
            Transform2D((x0, y0), angle0),
            Transform2D(T0.position, T0.angle),
            Transform2D(T0),
            Transform2D(B2D.b2Transform(B2D.b2Vec2(x0, y0), B2D.b2Rot(angle0)))
        ]

        print('T0 =', T0)

        for T0_alt in T0_alternatives:
            assert numpy.all(T0_alt.position == T0.position)
            assert numpy.isclose(T0_alt.angle, T0.angle)

        T0inv = T0.inverse()

        print('T0inv =', T0inv)

        T0T0inv = T0 * T0inv

        print('T0T0inv =', T0T0inv)
        assert numpy.abs(T0T0inv.position).max() < 1e-6
        assert T0T0inv.angle == 0.0

        T0invT0 = T0 * T0inv

        print('T0invT0 =', T0invT0)
        assert numpy.abs(T0invT0.position).max() < 1e-6
        assert T0invT0.angle == 0.0

        x1, y1 = numpy.random.random(2)*2 - 1
        angle1 = (numpy.random.random()*2-1) * numpy.pi

        T1 = Transform2D((x1, y1), angle1)
        
        x, y = numpy.random.random(2)*2 - 1
        p = numpy.array([x, y])
        print('p =', p)


        T0invT0p = T0.transform_inv(T0.transform_fwd(p))

        print('T0invT0p =', T0invT0p)

        assert numpy.all(numpy.isclose(T0invT0p, p))

        T0T0invp = T0.transform_fwd(T0.transform_inv(p))

        print('T0T0invp =', T0T0invp)

        assert numpy.all(numpy.isclose(T0T0invp, p, 1e-4))
        

        T1T0 = T1 * T0
        T1T0T0inv = T1T0 * T0.inverse()
        T1T0T0invT1inv = T1T0T0inv * T1.inverse()

        print('T1 =', T1)
        print('T1T0 =', T1T0)
        print('T1T0T0inv =', T1T0T0inv)
        print('T1T0T0invT1inv =', T1T0T0invT1inv)

        assert numpy.all(numpy.isclose(T1T0T0inv.position, T1.position, 1e-4))
        assert numpy.isclose(T1T0T0inv.angle, T1.angle)

        assert numpy.abs(T1T0T0invT1inv.position).max() < 1e-5
        assert numpy.abs(T1T0T0invT1inv.angle) < 1e-5
        

        print()

    T = Transform2D((2, 1), numpy.pi/2)

    pA = [0, 0]
    TpA = T * pA
    TpA_expected = [2, 1]

    pB = [1, 0]
    TpB = T * pB
    TpB_expected = [2, 2]

    pC = [0, 1]
    TpC = T * pC
    TpC_expected = [1, 1]

    print('T =', T)
    print('pA =', pA)
    print('TpA = ', TpA)
    assert numpy.all(numpy.isclose(TpA, TpA_expected))
    assert numpy.all(numpy.isclose(T.transform_inv(TpA), pA))
 
    print('pB =', pB)
    print('TpB = ', TpB)
    assert numpy.all(numpy.isclose(TpB, TpB_expected))
    assert numpy.all(numpy.isclose(T.transform_inv(TpB), pB))

    print('pC =', pC)
    print('TpC = ', TpC)
    assert numpy.all(numpy.isclose(TpC, TpC_expected))
    assert numpy.all(numpy.isclose(T.transform_inv(TpC), pC))

    print('...transforms seem to work OK!')

if __name__ == '__main__':

    _test_transform_2d()
    #_test_load_environment()
    
            
