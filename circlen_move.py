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

from .mode_enums import CNMoveMode, CommandMode

from .subject_state import SubjectStateMesh, SubjectStateObject, SubjectStateArmature, SubjectStatePoseBone, SubjectStateCurve

running = False

debug_draw_point_requests = []
debug_draw_point_requests3d = []
debug_draw_line_requests3d = []

class Pref:
    circle_back_color = (0.8,0.2,0.7,0.3)
    sphere_line_color = (.5,.5,.6,1)
    n_line_color = (.3,.3,.3,1)
    mos_point_color = (0.9,0.4,0.6,1)

class DrawRequests_Move:
    def __init__(self):
        self.circle3d_set = None
        self.n_set = None
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

    if draw_requests3d.n_set is not None:
        call_gl_xray(True)
        set = draw_requests3d.n_set
        p = set.begin + (set.begin - set.end)
        q = set.end
        draw_line3d_stipple(p,q, color=(.0,.2,.3,.4), width=1)

        bgl.glEnable(bgl.GL_POINT_SMOOTH)
        draw_point3d(set.begin, (0.8,0.3,0.5,1), 5 )
        bgl.glDisable(bgl.GL_POINT_SMOOTH)
        call_gl_xray(False)
        pass

    if draw_requests3d.uv_set is not None:
        set = draw_requests3d.uv_set
        p = set.p
        mj = set.major
        mi = set.minor
        k=set.radius*1

        call_gl_xray(True)
        r = (p - set.p_current).length
        draw_circle3d_stipple(p,mj,mi,r, color=(.0,.2,.3,.4), width=1)
        call_gl_xray(False)
        pass

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

class CircleNMovePanel(bpy.types.Panel):
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_context = ""
    bl_category = "Tools"
    bl_label = "Circle N Move"

    def draw(self, context):
        layout = self.layout
        layout.operator(CircleNMoveOperator.bl_idname, text=CircleNMoveOperator.bl_label)

class CircleNMoveOperator(bpy.types.Operator, DynamicMemberSetHelperMixin):
    bl_idname = "view3d.circle_n_move"
    bl_label = "Circle N Move"
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
                bpy.ops.view3d.circle_n_rot('INVOKE_DEFAULT')
                return {'FINISHED'}

            elif isinstance(mode_next, CNMoveMode):
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

class CommandParser:
    on_initial = CNMoveMode.DIR

    def __init__(self):
        self.__down__ = { 'rightmouse':False
                        , 'leftmouse':False
                        , 'shift':False
                        , 'alt':False
                        , 'ctrl':False
                        }
        self.force_next = None

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
            if event.type == 'R' and event.value == 'PRESS':
                return CommandMode.SWITCH_OPERATION_TO_ROT
            if event.type == 'S' and event.value == 'PRESS':
                return CommandMode.SWITCH_OPERATION_TO_SCALE

            if event.type == 'G' and event.value == 'PRESS':
                return CommandMode.PREVENT_DEFAULT

            if event.type == 'ESC' and event.value == 'PRESS':
                return CommandMode.CANCEL

        if event.type in ['Q', 'R', 'S', 'G', 'ESC', 'TAB']:
            return CommandMode.PREVENT_DEFAULT
        if ctrl_down and event.type == 'Z':
            return CommandMode.PREVENT_DEFAULT
        if event.type == 'C':
            self.force_next = CNMoveMode.DIR
            return CNMoveMode.CAPTURE_N

        elif left_press:
            return CommandMode.FINISH

        elif right_press and shift_down:
            return CNMoveMode.UV
        elif right_press:
            return CNMoveMode.N

        elif right_release and shift_down:
            return CNMoveMode.DIR
        elif right_release:
            return CNMoveMode.DIR

        elif shift_press and right_down:
            return CNMoveMode.UV

        elif shift_release and right_down:
            return CNMoveMode.N

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

    global debug_draw_point_requests
    global debug_draw_point_requests3d
    global debug_draw_line_requests3d

    if in_transform.mode_prev != modalvar.sphere_mode:
        subject.apply()

        in_transform.updatev('mode_prev', modalvar.sphere_mode)
        in_transform.updatev('base_mouse_r2d',   in_transform.prev_mouse_r2d.copy() )

        draw_requests3d.n_set = None
        draw_requests3d.uv_set = None
        if modalvar.sphere_mode == CNMoveMode.N:
            set = Object()
            p = subject.get_pivot()
            set.begin = p.copy()
            set.end = p + in_transform.n*10*radius
            draw_requests3d.n_set = set
        elif modalvar.sphere_mode == CNMoveMode.UV:
            p = subject.get_pivot()
            major, minor = calc_circle_directions_major_minor(context, p, in_transform.n)

            set = Object()
            set.p = p
            set.major = major
            set.minor = minor
            set.radius = radius
            set.p_current = subject.get_pivot()
            draw_requests3d.uv_set = set

    if draw_requests3d.uv_set is not None:
        draw_requests3d.uv_set.p_current = subject.get_latest_pivot()

    if modalvar.sphere_mode == CNMoveMode.DIR:
        if in_transform.force_normal:
            pass
        else:
            base_pivot = subject.get_pivot()
            mouse_on_sphere = calc_next_direction(context, mouse_r2d, base_pivot.copy(), radius)
            in_transform.updatev('n', (mouse_on_sphere - base_pivot).normalized() )

    elif modalvar.sphere_mode == CNMoveMode.UV:
        delta_uv = calc_transform_delta_move_uv( context
                                               , subject.get_pivot()
                                               , in_transform.n
                                               , mouse_r2d
                                               , in_transform.base_mouse_r2d
                                               , radius
                                               )
        delta = delta_uv
        subject.translate_relative(delta)

    elif modalvar.sphere_mode == CNMoveMode.N:
        delta_n = calc_transform_delta_move_n( context
                                             , in_transform.base_mouse_r2d
                                             , mouse_r2d
                                             , subject.get_pivot()
                                             , in_transform.n
                                             , radius
                                             )

        delta = delta_n
        subject.translate_relative(delta)

    elif modalvar.sphere_mode == CNMoveMode.CAPTURE_N:
        face_normal = get_face_normal_under_mouse(context, event)
        if face_normal is not None:
            in_transform.updatev('n', face_normal.normalized() )
            in_transform.updatev('force_normal', True)

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
    modalvar.in_transform.initv('force_normal', False )

    self.draw_requests3d = DrawRequests_Move()

    CircleNMoveOperator.bgl_draw_handler = bpy.types.SpaceView3D.draw_handler_add(bgl_draw_callback, (self.draw_requests3d,), 'WINDOW', 'POST_VIEW')
    self.initv('check__bgl_draw_handler', True)

    modalvar.initv('sphere_mode', CommandParser.on_initial)
    modalvar.initv('command_parser', CommandParser())

def pre_end_of_modal(self, context, event):
    global running

    running = False

    if self.existv('check__bgl_draw_handler'):
        bpy.types.SpaceView3D.draw_handler_remove(CircleNMoveOperator.bgl_draw_handler, 'WINDOW')
        self.cleanv('check__bgl_draw_handler')

    context.area.tag_redraw()

    self.modalvar.clean_allv()
    self.clean_allv()

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

def calc_transform_delta_move_uv(context, base_pivot, base_dir, mouse_r2d, base_mouse_r2d, radius):
    k = radius / 100
    l =  (mouse_r2d - base_mouse_r2d).length * k

    eu,ev = calc_circle_directions_major_minor(context, base_pivot, base_dir)

    vec_bm, loc_bm = region_2d_to_view_3d(context, base_mouse_r2d, base_pivot)

    _, loc_m = region_2d_to_view_3d(context, mouse_r2d, base_pivot)

    m = loc_m - loc_bm
    p = base_pivot
    p2d = view_3d_to_region_2d(context, p)
    m2d = view_3d_to_region_2d(context, p+m) - p2d
    eu2d = view_3d_to_region_2d(context, p+eu) - p2d
    ev2d = view_3d_to_region_2d(context, p+ev) - p2d

    m2d = m2d.normalized()
    eu2d = eu2d.normalized()
    ev2d = ev2d.normalized()

    a = eu2d.dot(m2d)*eu + ev2d.dot(m2d)*ev
    delta = a.normalized()*l

    return delta

def calc_transform_delta_move_uv0(context, base_pivot, base_dir, mouse_r2d, base_mouse_r2d, radius):
    k = radius / 100
    l =  (mouse_r2d - base_mouse_r2d).length * k

    vec_bm, loc_bm = region_2d_to_view_3d(context, base_mouse_r2d)
    eu = vec_bm.cross( base_dir )
    ev = eu.cross( base_dir )

    _, loc_m = region_2d_to_view_3d(context, mouse_r2d)
    m = loc_m - loc_bm
    a = eu.dot(m)*eu + ev.dot(m)*ev
    delta = a.normalized()*l
    return delta

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

def calc_transform_delta_move_n(context, base_mouse_r2d, mouse_r2d, pivot, n, radius):
    k = radius / 100

    p_r2d = view_3d_to_region_2d(context, pivot)
    t_r2d = view_3d_to_region_2d(context, pivot + n*1)
    if t_r2d is None:
        t_r2d = view_3d_to_region_2d(context, pivot - n*1)
        m = (t_r2d - p_r2d).normalized() * (-1)
    else:
        m = (t_r2d - p_r2d).normalized()
    k *= ( mouse_r2d - base_mouse_r2d ).normalized().dot(m)
    l =  (mouse_r2d - base_mouse_r2d).length * k

    delta_vector = n * l
    return delta_vector

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

        subject = MoveSubjectMesh(context.edit_object)
        return subject

    elif context.mode == 'OBJECT':
        if len( context.selected_objects ) == 0:
            return None

        subject = MoveSubjectObject(context.selected_objects)
        return subject

    elif context.mode == 'EDIT_ARMATURE':
        if len( [ eb for eb in context.edit_object.data.edit_bones if eb.select_head or eb.select_tail ] ) == 0:
            return None
        subject = MoveSubjectArmature(context.edit_object)
        return subject

    elif context.mode == 'POSE':
        sel_pose_bones = context.selected_pose_bones

        if len( sel_pose_bones ) == 0:
            return None

        subject = MoveSubjectPoseBone(context.active_object, sel_pose_bones)
        return subject
        pass
    elif context.mode in ['EDIT_CURVE', 'EDIT_SURFACE']:
        subject = MoveSubjectCurve(context.active_object)
        return subject

    return None

class MoveSubjectManipulation:
    def __init__(self, subject_state):
        self.prev_delta = Vector((0,0,0))
        self.subject_state = subject_state

    def __translate_relative__(self, delta):
        delta_delta = delta - self.prev_delta
        pe_sets = get_proportional_edit_settings()
        bpy.ops.transform.translate(value=delta_delta, proportional=pe_sets.proportional
                                                     , proportional_edit_falloff=pe_sets.proportional_edit_falloff
                                                     , proportional_size=pe_sets.proportional_size
                                                     )
        self.prev_delta = delta.copy()

    def translate_relative(self, delta):
        self.__translate_relative__(delta)
        self.subject_state.update_latest_state()

    def apply(self):
        self.prev_delta = Vector((0,0,0))

class MoveSubjectMixin:
    def translate_relative(self, delta):
        self.move_suject_manipulation.translate_relative(delta)
    def apply(self):
        self.subject_state.apply()
        self.move_suject_manipulation.apply()
    def restore_to_initial_state(self):
        return self.subject_state.restore_to_initial_state()
    def get_pivot(self):
        return self.subject_state.get_pivot()
    def get_latest_pivot(self):
        return self.subject_state.get_latest_pivot()

class MoveSubjectMesh(MoveSubjectMixin):
    def __init__(self, edit_object):
        self.subject_state = SubjectStateMesh(edit_object)
        self.move_suject_manipulation = MoveSubjectManipulation(self.subject_state)

class MoveSubjectObject(MoveSubjectMixin):
    def __init__(self, objects):
        self.subject_state = SubjectStateObject(objects)
        self.move_suject_manipulation = MoveSubjectManipulation(self.subject_state)

class MoveSubjectArmature(MoveSubjectMixin):
    def __init__(self, v):
        self.subject_state = SubjectStateArmature(v)
        self.move_suject_manipulation = MoveSubjectManipulation(self.subject_state)

class MoveSubjectPoseBone(MoveSubjectMixin):
    def __init__(self, active_object, selected_pose_bones):
        self.subject_state = SubjectStatePoseBone(active_object, selected_pose_bones)
        self.move_suject_manipulation = MoveSubjectManipulation(self.subject_state)

class MoveSubjectCurve(MoveSubjectMixin):
    def __init__(self, curve_object):
        self.subject_state = SubjectStateCurve(curve_object)
        self.move_suject_manipulation = MoveSubjectManipulation(self.subject_state)
def register():
    bpy.utils.register_class(CircleNMoveOperator)
def unregister():
    bpy.utils.unregister_class(CircleNMoveOperator)

if __name__ == "__main__":
    register()