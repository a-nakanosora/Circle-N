import bpy
import bmesh
import bgl
import math
from mathutils import Vector, Matrix

from .common_utils import (
      gl_xray
    , draw_point
    , draw_point3d
    , draw_line3d
    , draw_line3d_stipple
    , draw_circle
    , draw_circle3d
    , draw_circle3d_poly
    , draw_circle3d_stipple
    , restore_bgl
    , interp_color4f
    , region_2d_to_view_3d
    , view_3d_to_region_2d
    , get_viewpoint_coordinate
    , get_perpendicular_co
    , get_crossing_co_plane_line
    , get_nearest_co_line_line
    , get_face_normal_under_mouse
    , get_proportional_edit_settings
)

from .object_v import DynamicMemberSetHelperMixin, Object, ObjectV
from .mode_enums import CNRotMode, CommandMode

from .subject_state import SubjectStateMesh, SubjectStateObject, SubjectStateArmature, SubjectStatePoseBone, SubjectStateCurve

running = False

debug_draw_point_requests3d = []
debug_draw_line_requests3d = []

class Pref:
    circle_back_color = (0.2,0.8,0.7,0.3)
    sphere_line_color = (.5,.6,.5,1)
    n_line_color = (.3,.3,.3,1)
    mos_point_color = (0.4,0.9,0.8,1)

class DrawRequests_Rot:
    def __init__(self):
        self.circle3d_set = None
        self.uv_set = None
        self.enable_gl_xray = True

def bgl_draw_callback(draw_requests3d):
    call_gl_xray = gl_xray if draw_requests3d.enable_gl_xray else lambda _:None

    if draw_requests3d.circle3d_set is not None:
        c3d_set = draw_requests3d.circle3d_set

        p = c3d_set.p
        n = c3d_set.n
        radius = c3d_set.radius

        t = c3d_set.opt.get('cirle_viewangle', 1)
        circle_color = interp_color4f( Pref.circle_back_color, (1,1,1,0.3), t )
        sphere_line_color = Pref.sphere_line_color
        n_line_color = Pref.n_line_color
        mos_point_color = Pref.mos_point_color

        mouse_on_sphere = p + n * radius

        m = mouse_on_sphere
        mm = n
        vv = mm.cross( Vector((1,2,3)).normalized() )
        uu = mm.cross(vv)
        draw_line3d(p,m, color=n_line_color, width=5)

        draw_circle3d_poly(p,vv,uu,radius, color=circle_color)
        call_gl_xray(True)
        draw_circle3d(p,uu,mm,radius, width=1, color=sphere_line_color, half=True)
        draw_circle3d(p,vv,mm,radius, width=1, color=sphere_line_color, half=True)
        draw_circle3d(p,vv,uu,radius, color=(circle_color[0], circle_color[1], circle_color[2], .5))
        call_gl_xray(False)

        call_gl_xray(True)
        draw_line3d(p,m, color=n_line_color, width=2)

        bgl.glEnable(bgl.GL_POINT_SMOOTH)
        draw_point3d(mouse_on_sphere, mos_point_color, 10 )
        bgl.glDisable(bgl.GL_POINT_SMOOTH)
        call_gl_xray(False)

    if draw_requests3d.uv_set is not None:
        set = draw_requests3d.uv_set
        p = set.p
        mj = set.major
        mi = set.minor
        k=set.radius*10

        a = mj+mi
        b = mj-mi
        call_gl_xray(True)
        draw_line3d_stipple(p-k*a, p+k*a, color=(.0,.2,.3,.4), width=1)
        draw_line3d_stipple(p-k*b, p+k*b, color=(.0,.2,.3,.4), width=1)
        call_gl_xray(False)

    global debug_draw_point_requests3d
    global debug_draw_line_requests3d
    call_gl_xray(True)
    for o in debug_draw_point_requests3d:
        if isinstance(o, tuple):
            draw_point3d(o[0], o[1], o[2])
        else:
            draw_point3d(o)
    for o in debug_draw_line_requests3d:
        o = list(o)+[None]*10
        draw_line3d(o[0], o[1], o[2] or (0,0,0,1), o[3] or 1)
    call_gl_xray(False)

class Circle3dSet:
    def __init__(self, p, n, radius, opt = {}):
        self.p = p
        self.n = n
        self.radius = radius
        self.opt = opt

class CircleNRotPanel(bpy.types.Panel):
    bl_context = ""
    bl_region_type = "TOOLS"; bl_space_type = "VIEW_3D"; bl_category = "Tools"; bl_label = "Circle N Rot"
    def draw(self, context): layout = self.layout; layout.operator(CircleNRotOperator.bl_idname, text=CircleNRotOperator.bl_label)

class CircleNRotOperator(bpy.types.Operator, DynamicMemberSetHelperMixin):
    bl_idname = "view3d.circle_n_rot"
    bl_label = "Circle N Rot"
    bl_options = {'REGISTER', 'UNDO'}

    bgl_draw_handler = None

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'  \
                and context.mode in {'OBJECT', 'EDIT_MESH', 'EDIT_ARMATURE', 'POSE', 'EDIT_CURVE', 'EDIT_SURFACE'}

    def invoke(self, context, event):
        try:
            subject = get_subject(context)
            if subject is None:
                return {'CANCELLED'}

            global running
            if running is True:
                return {'CANCELLED'}
            running = True

            pre_begin_of_modal(self, context, event, subject)
        except:
            self.report({'WARNING'}, 'An error occurs. (invoke)')
            print('Error in invoke:')
            print_last_error()
            return {'CANCELLED'}
        context.window_manager.modal_handler_add(self)
        modal_redraw_main(context, event, self.draw_requests3d, self.modalvar)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        global running
        if running is False:
            return {'PASS_THROUGH'}

        try:
            mode_next = self.modalvar.command_parser.get_mode(event)
            if mode_next == CommandMode.FINISH:
                pre_end_of_modal(self, context, event)
                return {'FINISHED'}

            elif mode_next == CommandMode.MODAL:
                modal_redraw_main(context, event, self.draw_requests3d, self.modalvar)
                return {'RUNNING_MODAL'}

            elif mode_next == CommandMode.PASS:
                return {'PASS_THROUGH'}

            elif mode_next == CommandMode.PREVENT_DEFAULT:
                return {'RUNNING_MODAL'}

            elif mode_next == CommandMode.CANCEL:
                self.modalvar.subject.restore_to_initial_state()
                pre_end_of_modal(self, context, event)
                return {'CANCELLED'}

            elif mode_next == CommandMode.SWITCH_OPERATION_TO_MOVE:
                pre_end_of_modal(self, context, event)
                bpy.ops.view3d.circle_n_move('INVOKE_DEFAULT')
                return {'FINISHED'}
            elif mode_next == CommandMode.SWITCH_OPERATION_TO_ROT:
                pre_end_of_modal(self, context, event)
                bpy.ops.view3d.circle_n_rot('INVOKE_DEFAULT')
                return {'FINISHED'}
            elif mode_next == CommandMode.SWITCH_OPERATION_TO_SCALE:
                pre_end_of_modal(self, context, event)
                bpy.ops.view3d.circle_n_scale('INVOKE_DEFAULT')
                return {'FINISHED'}
            elif mode_next == CommandMode.SWITCH_OPERATION_TOGGLE:
                pre_end_of_modal(self, context, event)
                bpy.ops.view3d.circle_n_scale('INVOKE_DEFAULT')
                return {'FINISHED'}

            elif isinstance(mode_next, CNRotMode):
                self.modalvar.updatev('sphere_mode', mode_next)
                modal_redraw_main(context, event, self.draw_requests3d, self.modalvar)
                return {'RUNNING_MODAL'}

            else:
                raise Exception('unknown mode: %s' % mode_next)

        except:
            self.report({'WARNING'}, 'An error occurs. (modal)')
            print('Error in modal:')
            print_last_error()
            pre_end_of_modal(self, context, event)
            return {'FINISHED'}

def print_last_error():
    import sys
    print( sys.exc_info() )
    trb = sys.exc_info()[2]
    import traceback
    traceback.print_tb(trb)

def pre_begin_of_modal(self, context, event, subject):
    self.clean_allv()

    modalvar = ObjectV()
    self.initv('modalvar', modalvar)

    modalvar.initv('subject', subject)

    base_mouse_r2d = Vector((event.mouse_region_x, event.mouse_region_y))

    modalvar.initv('in_transform', ObjectV())
    modalvar.in_transform.initv('mode_prev', -1 )
    modalvar.in_transform.initv('base_mouse_r2d', base_mouse_r2d.copy() )
    modalvar.in_transform.initv('prev_mouse_r2d', base_mouse_r2d.copy() )
    modalvar.in_transform.initv('n', Vector((0,0,1)) )
    modalvar.in_transform.initv('base_n', Vector((0,0,1)) )
    modalvar.in_transform.initv('force_normal', False )

    self.draw_requests3d = DrawRequests_Rot()

    CircleNRotOperator.bgl_draw_handler = bpy.types.SpaceView3D.draw_handler_add(bgl_draw_callback, (self.draw_requests3d,), 'WINDOW', 'POST_VIEW')
    self.initv('check__bgl_draw_handler', True)

    modalvar.initv('sphere_mode', CommandParser.on_initial)
    modalvar.initv('command_parser', CommandParser())

def pre_end_of_modal(self, context, event):
    global running

    running = False

    if self.existv('check__bgl_draw_handler'):
        bpy.types.SpaceView3D.draw_handler_remove(CircleNRotOperator.bgl_draw_handler, 'WINDOW')
        self.cleanv('check__bgl_draw_handler')
    context.area.tag_redraw()

    self.modalvar.clean_allv()
    self.clean_allv()

class CommandParser:
    on_initial = CNRotMode.DIR

    def __init__(self):
        self.__down__ = { 'rightmouse':False
                        , 'leftmouse':False
                        , 'shift':False
                        , 'alt':False
                        , 'ctrl':False
                        }
        self.force_next = None
        self.__capture_n_fired__ = False

    def update_and_current_state(self, event, types, name):
        if event.type in types:
            self.__down__[name] = event.value == 'PRESS'
        press = event.type in types and event.value == 'PRESS'
        release = event.type in types and event.value == 'RELEASE'
        return press, release, self.__down__[name]

    def get_mode(self, event):
        if self.force_next is not None:
            forced = self.force_next
            self.force_next = None
            return forced

        left_press, left_release, left_down = self.update_and_current_state(event, ['LEFTMOUSE'], 'leftmouse')
        right_press, right_release, right_down = self.update_and_current_state(event, ['RIGHTMOUSE'], 'rightmouse')
        shift_press, shift_release, shift_down = self.update_and_current_state(event, ['LEFT_SHIFT', 'RIGHT_SHIFT'], 'shift')
        alt_press, alt_release, alt_down = self.update_and_current_state(event, ['LEFT_ALT', 'RIGHT_ALT'], 'alt')
        ctrl_press, ctrl_release, ctrl_down = self.update_and_current_state(event, ['LEFT_CTRL', 'RIGHT_CTRL'], 'ctrl')

        if not left_down and not right_down:
            if event.type == 'Q' and event.value == 'PRESS':
                return CommandMode.SWITCH_OPERATION_TOGGLE
            if event.type == 'G' and event.value == 'PRESS':
                return CommandMode.SWITCH_OPERATION_TO_MOVE
            if event.type == 'S' and event.value == 'PRESS':
                return CommandMode.SWITCH_OPERATION_TO_SCALE

            if event.type == 'R' and event.value == 'PRESS':
                return CommandMode.PREVENT_DEFAULT

            if event.type == 'ESC' and event.value == 'PRESS':
                return CommandMode.CANCEL

        if event.type in ['Q', 'R', 'S', 'G', 'ESC', 'TAB']:
            return CommandMode.PREVENT_DEFAULT
        if ctrl_down and event.type == 'Z':
            return CommandMode.PREVENT_DEFAULT
        if event.type == 'C':
            self.force_next = CNRotMode.DIR
            self.__capture_n_fired__ = True
            return CNRotMode.CAPTURE_N

        elif left_press:
            return CommandMode.FINISH

        elif right_press and shift_down:
            return CNRotMode.UV_ROT
        elif right_press:
            if self.__capture_n_fired__:
                return CNRotMode.UV_ROT
            else:
                return CNRotMode.DIR_ROT

        elif right_release and shift_down:
            return CNRotMode.DIR
        elif right_release:
            return CNRotMode.DIR

        elif shift_press and right_down:
            return CNRotMode.UV_ROT
        elif shift_release and right_down:
            return CNRotMode.UV_ROT

        elif event.type == 'MOUSEMOVE':
            return CommandMode.MODAL

        return CommandMode.PASS

def modal_redraw_main(context, event, draw_requests3d, modalvar):
    subject = modalvar.subject
    mouse_r2d = Vector((event.mouse_region_x, event.mouse_region_y))
    in_transform = modalvar.in_transform

    if not in_transform.existv('radius'):
        in_transform.initv('radius', calc_radius( context, subject.get_pivot(), mouse_r2d ))
    radius = in_transform.radius

    global debug_draw_point_requests3d
    global debug_draw_line_requests3d

    debug_draw_point_requests3d = []
    debug_draw_line_requests3d = []

    if in_transform.mode_prev != modalvar.sphere_mode:
        subject.apply()

        if in_transform.mode_prev == CNRotMode.DIR:
            in_transform.updatev('base_n', in_transform.n.copy())

        in_transform.updatev('mode_prev', modalvar.sphere_mode)
        in_transform.updatev('base_mouse_r2d',   in_transform.prev_mouse_r2d.copy() )

        draw_requests3d.uv_set = None
        if modalvar.sphere_mode == CNRotMode.UV_ROT:
            p = subject.get_pivot()
            major, minor = calc_circle_directions_major_minor(context, p, in_transform.n)

            set = Object()
            set.p = p
            set.major = major
            set.minor = minor
            set.radius = radius
            set.p_current = subject.get_pivot()
            draw_requests3d.uv_set = set

    if modalvar.sphere_mode == CNRotMode.DIR:
        if in_transform.force_normal:
            pass
        else:
            base_pivot = subject.get_pivot()
            mouse_on_sphere = calc_next_direction(context, mouse_r2d, base_pivot.copy(), radius)
            in_transform.updatev('n', (mouse_on_sphere - base_pivot).normalized() )

    elif modalvar.sphere_mode == CNRotMode.CAPTURE_N:
        face_normal = get_face_normal_under_mouse(context, event)
        if face_normal is not None:
            in_transform.updatev('n', face_normal.normalized() )
            in_transform.updatev('force_normal', True)

    elif modalvar.sphere_mode == CNRotMode.DIR_ROT:
        base_pivot = subject.get_pivot()
        mouse_on_sphere = calc_next_direction(context, mouse_r2d, base_pivot.copy(), radius)

        n0 = in_transform.n
        n1 = (mouse_on_sphere - base_pivot).normalized()
        in_transform.updatev('n', n1.copy() )

        temp = n0.cross(n1)
        m = temp.normalized()

        theta = math.acos( min(1, n0.dot(n1)) )
        pe_sets = get_proportional_edit_settings()
        bpy.ops.transform.rotate(value=theta, axis=m
                                , proportional=pe_sets.proportional
                                , proportional_edit_falloff=pe_sets.proportional_edit_falloff
                                , proportional_size=pe_sets.proportional_size
                                )
    elif modalvar.sphere_mode == CNRotMode.UV_ROT:
        n = in_transform.n
        p = subject.get_pivot()

        _, q = region_2d_to_view_3d(context, mouse_r2d, p)

        if not in_transform.existv('uv_rot_q0'):
            vec_q0, q0 = region_2d_to_view_3d(context, mouse_r2d, p)
            in_transform.initv('uv_rot_q0', q0)
        q0 = in_transform.uv_rot_q0

        m0 = (q0 - p).normalized()
        m = (q - p).normalized()

        theta = math.acos( min(1, m0.dot(m)) )
        theta *= math.copysign(1, n.cross(m0).dot(m))
        if (q-p).length < radius:
            theta *= (q-p).length/radius

        if abs(theta) < 40*math.pi/180:
            pe_sets = get_proportional_edit_settings()
            bpy.ops.transform.rotate(value=theta, axis=n
                                    , proportional=pe_sets.proportional
                                    , proportional_edit_falloff=pe_sets.proportional_edit_falloff
                                    , proportional_size=pe_sets.proportional_size
                                    )

        in_transform.updatev('uv_rot_q0', q)

    else:
        raise Exception('invalid sphere_mode: ', modalvar.sphere_mode)

    in_transform.updatev('prev_mouse_r2d', mouse_r2d )

    vec, _ = get_viewpoint_coordinate(context)
    vec *= -1
    opt = {'cirle_viewangle': (in_transform.n.dot(vec)+1)/2}
    draw_requests3d.circle3d_set = Circle3dSet( subject.get_latest_pivot().copy()
                                            , in_transform.n.copy()
                                            , radius
                                            , opt
                                            )
    draw_requests3d.enable_gl_xray = context.space_data.viewport_shade != 'WIREFRAME'
    context.area.tag_redraw()

def restore_vert_coords(edit_object, base_vert_coords):
    sel_verts = [v for v in bmesh.from_edit_mesh(edit_object.data).verts if v.select]
    for v, base_co in zip(sel_verts, base_vert_coords):
        v.co = base_co

def calc_next_direction(context, mouse_r2d, pivot, radius):
    pivot_r2d = view_3d_to_region_2d(context, pivot)
    pivot_r2d_epx = pivot_r2d + Vector((1, 0)) * 10
    vec_piv_epx, loc_piv_epx = region_2d_to_view_3d(context, pivot_r2d_epx)
    pivot_epx = get_perpendicular_co(loc_piv_epx, vec_piv_epx, pivot)

    vec_m, loc_m = region_2d_to_view_3d(context, mouse_r2d)

    mn_z = -vec_m.normalized()

    if context.space_data.region_3d.view_perspective == 'PERSP':
        vec_sight, loc_sight = get_viewpoint_coordinate(context)
        mouse_view3d = get_crossing_co_plane_line( pivot, (loc_sight - pivot).normalized(), loc_m, vec_m )
    else:
        mouse_view3d = get_crossing_co_plane_line( pivot, mn_z, loc_m, vec_m )

    offset = mn_z*radius
    mp_view3d_offset = mouse_view3d + offset
    pivot_offset = pivot + offset
    mp_view3d_offset += -mn_z * ((pivot_offset-mp_view3d_offset).length/(3*radius))**2 *radius
    mouse_on_sphere = pivot + (mp_view3d_offset-pivot).normalized() * radius

    return mouse_on_sphere

def calc_circle_directions_major_minor(context, p, n):
    n = n.normalized()
    p2d = view_3d_to_region_2d(context, p)
    t2d = view_3d_to_region_2d(context, p + n*1)
    if t2d is None:
        t2d = view_3d_to_region_2d(context, p - n*1)
        m2d = (t2d - p2d).normalized() * (-1)
    else:
        m2d = (t2d - p2d).normalized()

    u2d = Vector((m2d.y, -m2d.x))

    _, u = region_2d_to_view_3d(context, p2d+u2d, p)
    e_major = (u - p).normalized()
    e_minor = n.cross(e_major)
    return e_major, e_minor

def calc_radius(context, pivot, mouse_r2d):
    pivot_r2d = view_3d_to_region_2d(context, pivot)
    pivot_r2d_epx = pivot_r2d + Vector((1, 0)) * 10
    vec_piv_epx, loc_piv_epx = region_2d_to_view_3d(context, pivot_r2d_epx)

    pivot_epx = get_perpendicular_co(loc_piv_epx, vec_piv_epx, pivot)
    pivot_epx = pivot + (pivot_epx - pivot).normalized()

    vec_m, loc_m = region_2d_to_view_3d(context, mouse_r2d)

    let_va, let_a = region_2d_to_view_3d(context, Vector((100, 100)))
    let_vb, let_b = region_2d_to_view_3d(context, Vector((100, 100+100)))
    let_a = get_perpendicular_co(let_a, let_va, pivot)
    let_b = get_perpendicular_co(let_b, let_vb, pivot)
    radius = (let_b - let_a).length
    return radius

def get_subject(context):
    if context.area.type != 'VIEW_3D':
        return None

    if context.mode == 'EDIT_MESH':
        if len( [v for v in bmesh.from_edit_mesh(context.edit_object.data).verts if v.select] ) == 0:
            return None

        subject = RotSubjectMesh(context.edit_object)
        return subject

    elif context.mode == 'OBJECT':
        if len( context.selected_objects ) == 0:
            return None

        subject = RotSubjectObject(context.selected_objects)
        return subject

    elif context.mode == 'EDIT_ARMATURE':
        if len( [ eb for eb in context.edit_object.data.edit_bones if eb.select_head or eb.select_tail ] ) == 0:
            return None
        subject = RotSubjectArmature(context.edit_object)
        return subject

    elif context.mode == 'POSE':
        sel_pose_bones = context.selected_pose_bones

        if len( sel_pose_bones ) == 0:
            return None

        subject = RotSubjectPoseBone(context.active_object, sel_pose_bones)
        return subject
        pass
    elif context.mode in ['EDIT_CURVE', 'EDIT_SURFACE']:
        subject = RotSubjectCurve(context.active_object)
        return subject

    return None

class RotSubjectMesh(SubjectStateMesh):
    pass

class RotSubjectObject(SubjectStateObject):
    pass

class RotSubjectArmature(SubjectStateArmature):
    pass

class RotSubjectPoseBone(SubjectStatePoseBone):
    pass

class RotSubjectCurve(SubjectStateCurve):
    pass

def register():
    bpy.utils.register_class(CircleNRotOperator)

def unregister():
    bpy.utils.unregister_class(CircleNRotOperator)

if __name__ == "__main__":
    register()