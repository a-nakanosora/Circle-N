import bpy
import bmesh
from mathutils import Vector, Matrix
from collections import namedtuple
class SubjectState:
    def __init__(self):
        self.initial_state = self.get_latest_state()
        self.base_state = self.get_latest_state()
        self.latest_state = self.get_latest_state()

    def __get_latest_state__(self):
        raise Exception('not implemented.')
        return []

    def __get_pivot__(self, state):
        raise Exception('not implemented.')
        return Vector((0,0,0))

    def __restore__(self, state):
        raise Exception('not implemented.')

    def get_pivot(self):
        return self.__get_pivot__(self.base_state)

    def get_latest_pivot(self):
        return self.__get_pivot__(self.latest_state)

    def get_initial_pivot(self):
        return self.__get_pivot__(self.initial_state)

    def restore(self):
        self.__restore__(self.base_state)
        self.latest_state = self.base_state.copy()

    def restore_to_initial_state(self):
        self.__restore__(self.initial_state)
        self.latest_state = self.initial_state.copy()

    def apply(self):
        self.base_state = self.latest_state.copy()

    def get_latest_state(self): return self.__get_latest_state__()

    def update_latest_state(self):
        self.latest_state = self.get_latest_state()
class SubjectStateMesh(SubjectState):
    type = 'mesh'
    def __init__(self, edit_object):
        self.mesh = edit_object.data
        self.edit_object = edit_object
        super().__init__()

    def __restore__(self, state):
        sel_verts = [v for v in bmesh.from_edit_mesh(self.mesh).verts if v.select]
        for v, base_co in zip(sel_verts, state):
            v.co = base_co

    def __get_pivot__(self, state):
        sel_coords = state
        return self.edit_object.matrix_world * ( sum(sel_coords, Vector()) / len(sel_coords) )

    def __get_latest_state__(self):
        bm = bmesh.from_edit_mesh(bpy.context.edit_object.data)
        sel_coords = [v.co.copy() for v in bm.verts if v.select]
        return sel_coords

class SubjectStateObject(SubjectState):
    type = 'object'
    def __init__(self, objects):
        self.objects = objects
        super().__init__()
    def __restore__(self, state):
        for obj, matrix_world in zip(self.objects, state):
            obj.matrix_world = matrix_world.copy()

    def __get_pivot__(self, state):
        sel_state = [matrix_world.translation for matrix_world in state]
        return sum(sel_state, Vector()) / len(sel_state)

    def __get_latest_state__(self):
        return [obj.matrix_world.copy() for obj in self.objects]

class SubjectStateArmature(SubjectState):
    def __init__(self, edit_object):
        self.edit_bones = edit_object.data.edit_bones
        self.edit_object = edit_object
        super().__init__()
    def __restore__(self, state):
        for eb, head, tail in state:
            if head:
                eb.head = head.copy()
            if tail:
                eb.tail = tail.copy()

    def __get_pivot__(self, state):
        ls = []
        for eb, head, tail in state:
            if head:
                ls.append(head)
            if tail:
                ls.append(tail)
        ave_co = sum(ls, Vector()) / len(ls)
        return self.edit_object.matrix_world * ave_co

    def __get_latest_state__(self):
        sel_bones_state =[]
        for eb in self.edit_bones:
            head_co = eb.head.copy() if eb.select_head else None
            tail_co = eb.tail.copy() if eb.select_tail else None
            if head_co or tail_co:
                sel_bones_state.append( (eb, head_co, tail_co) )

        return sel_bones_state

class SubjectStatePoseBone(SubjectState):
    def __init__(self, active_object, selected_pose_bones):
        self.selected_pose_bones = selected_pose_bones
        self.object = active_object
        super().__init__()

    def __restore__(self, state):
        for pb, matrix in state:
            pb.matrix = matrix.copy()
            bpy.context.scene.update()

    def __get_pivot__(self, state):
        matrix_world = self.object.matrix_world
        sel_coords = [(matrix_world * m).translation for pb, m in state]
        return sum(sel_coords, Vector()) / len(sel_coords)

    def __get_latest_state__(self):
        return [(pose_bone, pose_bone.matrix.copy()) for pose_bone in self.object.pose.bones if pose_bone.bone.select]

        res = []
        for pose_bone in self.object.pose.bones:
            if pose_bone.bone.select:
                m = pose_bone.matrix.copy()
                m.translation = pose_bone.tail.copy()
                res.append( (pose_bone, m) )
        return res

class SubjectStateCurve(SubjectState):
    def __init__(self, curve_object :bpy.types.Object):
        assert isinstance(curve_object.data, bpy.types.Curve)
        self.curve_object = curve_object
        self.curve = curve_object.data
        super().__init__()

    def __restore__(self, state):
        for pointrefs, bezierrefs in state:
            for pt, co in pointrefs:
                pt.co = co.copy()
            for bz, co, hl, hr in bezierrefs:
                bz.co = co.copy()
                bz.handle_left = hl.copy()
                bz.handle_right = hr.copy()

    def __get_pivot__(self, state):
        selected_all_co = []
        for pointrefs, bezierrefs in state:
            for pt, _ in pointrefs:
                if pt.select:
                    selected_all_co.append( pt.co.copy() )
            for bz, _, _, _ in bezierrefs:
                if bz.select_control_point:
                    selected_all_co.append( bz.co.copy() )
                if bz.select_left_handle:
                    selected_all_co.append( bz.handle_left.copy() )
                if bz.select_right_handle:
                    selected_all_co.append( bz.handle_right.copy() )

        selected_all_co = [co.to_3d() for co in selected_all_co]

        m = self.curve_object.matrix_world
        selected_all_co = [m*co for co in selected_all_co]

        return sum(selected_all_co, Vector()) / len(selected_all_co)

    def __get_latest_state__(self):
        PointRef = namedtuple('PointRef', 'point co')
        BezierPointRef = namedtuple('BezierPointRef', 'bezier_point co handle_left handle_right')
        CurveState = namedtuple('CurveState', 'pointrefs bezierrefs')

        curve = self.curve
        state = []
        for sp in curve.splines:
            pointrefs = [ PointRef( pt, pt.co.copy() )  for pt in sp.points]
            bezierrefs = [ BezierPointRef( bz, bz.co.copy(), bz.handle_left.copy(), bz.handle_right.copy() )  for bz in sp.bezier_points]
            state.append( CurveState( pointrefs, bezierrefs ) )

        return state