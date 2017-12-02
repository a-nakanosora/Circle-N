bl_info = {
    "name": "Circle N",
    "description": "Axis free manipulator with circle based GUI.",
    "author": "A Nakanosora",
    "version": (1, 0),
    "blender": (2, 74, 0),
    "location": "View3D",
    "category": "3D View"
}

if "bpy" in locals():
    import imp
    imp.reload(circlen_move)
    imp.reload(circlen_rot)
    imp.reload(circlen_scale)
else:
    from . import circlen_move
    from . import circlen_rot
    from . import circlen_scale

import bpy

class CircleNPanel(bpy.types.Panel):
    bl_region_type = "TOOLS"
    bl_space_type = "VIEW_3D"
    bl_context = ""
    bl_category = "Tools"
    bl_label = "Circle N"

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'  \
                and context.mode in {'OBJECT', 'EDIT_MESH', 'EDIT_ARMATURE', 'POSE', 'EDIT_CURVE', 'EDIT_SURFACE'}

    def draw(self, context):
        layout = self.layout
        layout.operator(circlen_move.CircleNMoveOperator.bl_idname, text='Move')
        layout.operator(circlen_rot.CircleNRotOperator.bl_idname, text='Rotate')
        layout.operator(circlen_scale.CircleNScaleOperator.bl_idname, text='Scale')

addon_keymaps = []

def register():
    circlen_move.register()
    circlen_rot.register()
    circlen_scale.register()
    bpy.utils.register_class(CircleNPanel)

    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new(circlen_move.CircleNMoveOperator.bl_idname, 'Q', 'PRESS')
    addon_keymaps.append(km)

def unregister():
    circlen_move.unregister()
    circlen_rot.unregister()
    circlen_scale.unregister()
    bpy.utils.unregister_class(CircleNPanel)

    wm = bpy.context.window_manager
    for km in addon_keymaps:
        for kmi in km.keymap_items[:]:
           if kmi.idname == circlen_move.CircleNMoveOperator.bl_idname:
                km.keymap_items.remove(kmi)
        wm.keyconfigs.addon.keymaps.remove(km)
    addon_keymaps.clear()

if __name__ == "__main__":
    register()