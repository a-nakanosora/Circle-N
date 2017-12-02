import bpy
import bmesh
import bgl
import math
import bpy_extras.view3d_utils
from mathutils import Vector, Matrix

def gl_xray(turn_on=True):
    if turn_on:
        bgl.glDisable(bgl.GL_DEPTH_TEST)
    else:
        bgl.glEnable(bgl.GL_DEPTH_TEST)

def draw_point(p, color=(0,0,0,1), size=4):
    bgl.glPointSize(size)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_POINTS)
    bgl.glColor4f( color[0], color[1], color[2], color[3], )
    bgl.glVertex2f(p[0], p[1])
    bgl.glEnd()
    restore_bgl()

def draw_point3d(p, color=(0,0,0,1), size=4):
    bgl.glPointSize(size)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_POINTS)
    bgl.glColor4f( color[0], color[1], color[2], color[3], )
    bgl.glVertex3f(p[0], p[1], p[2])
    bgl.glEnd()
    restore_bgl()

def draw_line3d(a,b, color=(0,0,0,1), width=1):
    bgl.glLineWidth(width)
    bgl.glColor4f( color[0], color[1], color[2], color[3], )
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_LINE_STRIP)
    bgl.glVertex3f(a[0], a[1], a[2])
    bgl.glVertex3f(b[0], b[1], b[2])
    bgl.glEnd()
    restore_bgl()

def draw_line3d_stipple(a,b, color=(0,0,0,1), width=1, line_stipple=True):
    if line_stipple:
        bgl.glEnable(bgl.GL_LINE_STIPPLE)
        bgl.glLineStipple(1, 0xe73c)
    bgl.glLineWidth(width)
    bgl.glColor4f( color[0], color[1], color[2], color[3], )
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_LINE_STRIP)
    bgl.glVertex3f(a[0], a[1], a[2])
    bgl.glVertex3f(b[0], b[1], b[2])
    bgl.glEnd()
    if line_stipple:
        bgl.glDisable(bgl.GL_LINE_STIPPLE)

    restore_bgl()

def draw_circle(center, radius):
    bgl.glPointSize(1)
    bgl.glColor4f(0,0,0,1)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_LINE_STRIP);

    r = radius
    t=0
    x0 = center.x
    y0 = center.y
    dt = math.pi*2/20
    while t<math.pi*2:
        bgl.glVertex2f( x0+r*math.cos(t), y0+r*math.sin(t) )
        t += dt
    t=math.pi*2

    bgl.glVertex2f( x0+r*math.cos(t), y0+r*math.sin(t) )
    bgl.glEnd()
    restore_bgl()

def draw_circle3d(p,u,v, radius, color=(0,0,0,1), width=1, half=False):
    u = u.normalized()
    v = v.normalized()
    bgl.glPointSize(1)
    bgl.glLineWidth(width)
    bgl.glColor4f( color[0], color[1], color[2], color[3])
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_LINE_STRIP);

    r = radius
    t=0
    last = math.pi*2 if not half else math.pi
    dt = last/20
    while t<last:
        q = p + r*math.cos(t)*u + r*math.sin(t)*v
        bgl.glVertex3f( q.x, q.y, q.z )
        t += dt
    t=last
    q = p + r*math.cos(t)*u + r*math.sin(t)*v
    bgl.glVertex3f( q.x, q.y, q.z )
    bgl.glEnd()
    restore_bgl()

def draw_circle3d_poly(p,u,v, radius, color=(0,0,0,1), width=1, half=False):
    u = u.normalized()
    v = v.normalized()
    bgl.glPointSize(1)
    bgl.glColor4f( color[0], color[1], color[2], color[3])
    bgl.glLineWidth(width)
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_POLYGON);

    r = radius
    t=0
    last = math.pi*2 if not half else math.pi
    dt = last/20
    while t<last:
        q = p + r*math.cos(t)*u + r*math.sin(t)*v
        bgl.glVertex3f( q.x, q.y, q.z )
        t += dt
    t=last
    q = p + r*math.cos(t)*u + r*math.sin(t)*v
    bgl.glVertex3f( q.x, q.y, q.z )
    bgl.glEnd()
    restore_bgl()

def draw_circle3d_stipple(p,u,v, radius, color=(0,0,0,1), width=1, half=False):
    u = u.normalized()
    v = v.normalized()

    bgl.glEnable(bgl.GL_LINE_STIPPLE)
    bgl.glLineStipple(1, 0xe73c)
    bgl.glPointSize(1)
    bgl.glLineWidth(width)
    bgl.glColor4f( color[0], color[1], color[2], color[3])
    bgl.glEnable(bgl.GL_BLEND)
    bgl.glBegin(bgl.GL_LINE_STRIP);

    r = radius
    t=0
    last = math.pi*2 if not half else math.pi
    dt = last/20
    while t<last:
        q = p + r*math.cos(t)*u + r*math.sin(t)*v
        bgl.glVertex3f( q.x, q.y, q.z )
        t += dt
    t=last
    q = p + r*math.cos(t)*u + r*math.sin(t)*v
    bgl.glVertex3f( q.x, q.y, q.z )
    bgl.glEnd()
    bgl.glDisable(bgl.GL_LINE_STIPPLE)
    restore_bgl()

def restore_bgl():
    bgl.glLineWidth(1)
    bgl.glDisable(bgl.GL_BLEND)
    bgl.glColor4f(0.0, 0.0, 0.0, 1.0)

def interp_color4f(c0, c1, t):
    def f(t): d=2; e=10; return 1/2*(2*t)**d if t<=1/2 else 1-1/2*(2*(1-t))**(d+e)
    return [a+(b-a)*f(t) for a,b in zip(c0,c1)]

def region_2d_to_view_3d(context, pos2d, depth_location=None):
    region = context.region
    rv3d = context.space_data.region_3d
    vec3d = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, pos2d)

    if depth_location is None:
        vec, viewpoint = get_viewpoint_coordinate(context)
        depth_location = viewpoint + vec

    loc3d = bpy_extras.view3d_utils.region_2d_to_location_3d(region, rv3d, pos2d, depth_location)
    return vec3d, loc3d

def view_3d_to_region_2d(context, co, local_to_global=False):
    area = context.area
    if area.type != 'VIEW_3D':
        raise Exception('view_3d_to_region_2d Error: invalid context.')
    viewport = area.regions[4]

    if local_to_global:
        co_3d = context.edit_object.matrix_world * co
    else:
        co_3d = co
    co_2d = bpy_extras.view3d_utils.location_3d_to_region_2d(viewport, area.spaces[0].region_3d, co)
    return co_2d

def get_viewpoint_coordinate(context):
    region = context.region
    rv3d = context.space_data.region_3d
    p2d = Vector((region.width/2, region.height/2))
    viewpoint = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, p2d)
    center_vec = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, p2d)
    return center_vec, viewpoint

def get_perpendicular_co(p,n,a):
    return p + (a-p).dot(n) * n

def get_crossing_co_plane_line(p,n, a,m):
    w = (p-a).dot(n) / m.dot(n)
    return a + w*m

def get_nearest_co_line_line(p,u,q,v):
    s = ( (p-q).dot(u) - ((p-q).dot(v))*v.dot(u) )/(v.dot(u)**2 - 1)
    return p + s*u

def get_face_normal_under_mouse(context, event):
    normal, obj_matrix = get_nearest_object_face_under_mouse(context, event)
    if normal is not None:
        scale = Matrix().to_3x3()
        m_world = obj_matrix.copy()
        rot = obj_matrix.normalized()
        for i in range(3):
            scale[i][i] = rot[i][i] / m_world[i][i]

        return rot.to_3x3() * scale * normal
    else:
        return None

def get_nearest_object_face_under_mouse(context, event, ray_max=1000.0):
    scene = context.scene
    region = context.region
    rv3d = context.region_data
    coord = event.mouse_region_x, event.mouse_region_y
    view_vector = bpy_extras.view3d_utils.region_2d_to_vector_3d(region, rv3d, coord)
    ray_origin = bpy_extras.view3d_utils.region_2d_to_origin_3d(region, rv3d, coord)

    ray_target = ray_origin + (view_vector * ray_max)

    def visible_objects_and_duplis():
        for obj in context.visible_objects:
            if obj.type == 'MESH':
                yield (obj, obj.matrix_world.copy())

            if obj.dupli_type != 'NONE':
                obj.dupli_list_create(scene)
                for dob in obj.dupli_list:
                    obj_dupli = dob.object
                    if obj_dupli.type == 'MESH':
                        yield (obj_dupli, dob.matrix.copy())

            obj.dupli_list_clear()

    def obj_ray_cast(obj, matrix):
        matrix_inv = matrix.inverted()
        ray_origin_obj = matrix_inv * ray_origin
        ray_target_obj = matrix_inv * ray_target
        ray_direction_obj = ray_target_obj - ray_origin_obj
        success, location, normal, face_index = obj.ray_cast(ray_origin_obj, ray_direction_obj)

        if success:
            return location, normal, face_index
        else:
            return None, None, None
    best_length_squared = ray_max * ray_max
    best_obj_matrix = None
    best_normal = None

    tempmesh = bpy.data.meshes.new('_circlen_temp')
    tempobj = bpy.data.objects.new('_circlen_temp', tempmesh)
    scene.objects.link(tempobj)
    scene.update()

    for obj, matrix in visible_objects_and_duplis():
        if obj.type == 'MESH':
            if context.mode == 'EDIT_MESH':
                bpy.ops.object.editmode_toggle()
                bpy.ops.object.editmode_toggle()

            me = obj.to_mesh(scene=scene, apply_modifiers=True, settings='PREVIEW')
            tempobj.data = me
            scene.update()
            hit, normal, face_index = obj_ray_cast(tempobj, matrix)
            tempobj.data = tempmesh
            bpy.data.meshes.remove(me)

            if hit is not None:
                hit_world = matrix * hit
                length_squared = (hit_world - ray_origin).length_squared
                if length_squared < best_length_squared:
                    best_length_squared = length_squared
                    best_obj_matrix = obj.matrix_world.copy()
                    best_normal = normal.copy()

    scene.objects.unlink(tempobj)
    bpy.data.objects.remove(tempobj)
    bpy.data.meshes.remove(tempmesh)
    scene.update()

    return best_normal, best_obj_matrix

def get_proportional_edit_settings():
    import bpy
    context = bpy.context
    settings = context.scene.tool_settings
    if context.mode == 'OBJECT':
        proportional = 'ENABLED' if settings.use_proportional_edit_objects else 'DISABLED'

    elif context.mode == 'EDIT_MESH':
        proportional = settings.proportional_edit

    elif context.mode in ['POSE', 'EDIT_ARMATURE']:
        proportional = 'DISABLED'
    else:
        proportional = 'DISABLED'

    class Object:pass
    res = Object()
    res.proportional = proportional
    res.proportional_edit_falloff = settings.proportional_edit_falloff
    res.proportional_size = settings.proportional_size
    return res