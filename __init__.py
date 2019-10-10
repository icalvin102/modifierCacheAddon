bl_info = {
    "name": "Modifier Cache",
    "author": "icalvin102 // icalvin.de",
    "version": (1, 0),
    "blender": (2, 81, 0),
    "location": "Properties > Modifiers",
    "description": "",
    "warning": "",
    "wiki_url": "",
    "category": "Import-Export",
}


import bpy
import os

handler_frame_update_running = False

def abspath(filepath):
    return os.path.expanduser(bpy.path.abspath(filepath))

def create_filepath(fp, frame):
    return f'{abspath(fp)}_{frame:05d}.abc'

def handler_update_filepath(self, context):
    print(create_filepath(self.filepath, self.frame_start))


def handler_toggle_mesh_source(self, context):
    if self.enabled:
        self.original_data = bpy.data.meshes.new_from_object(context.object)
        self.original_data.name = context.object.data.name + '.original'
    else:
        context.object.data = self.original_data
        context.object.data.name = context.object.data.name.replace('.original', '')
     
    
def filter_renderable_objects(self, context):
    return context.type in ['MESH', 'META', 'SURFACE', 'CURVE']

@bpy.app.handlers.persistent
def handler_frame_update(scene):
    global handler_frame_update_running
    if handler_frame_update_running:
        return
    handler_frame_update_running = True
    for obj in bpy.data.objects:
        mss = obj.mesh_source_settings
        mcs = obj.modifier_cache_settings
        
        if not mss.enabled and mcs.use_cache:
            continue
    
        src_obj = mss.source_object
        if src_obj:
            if mss.use_modifiers:
                depsgraph = bpy.context.evaluated_depsgraph_get()
                src_obj = src_obj.evaluated_get(depsgraph)
                pass
            old_mesh = obj.data
            new_mesh = bpy.data.meshes.new_from_object(src_obj)
            obj.data = new_mesh
            bpy.data.meshes.remove(old_mesh)
    handler_frame_update_running = False

    
class ModifierVisibilitySettings(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name='Modifier Name')
    show_viewport: bpy.props.BoolProperty(name='Show Viewport', default=True)
    show_render: bpy.props.BoolProperty(name='Show Render', default=True)

class ModifierCacheSettings(bpy.types.PropertyGroup):
    frame_start: bpy.props.IntProperty(name='Start Frame', default=0, min=0)
    frame_end: bpy.props.IntProperty(name='End Frame', default=250, min=0)
    
    filepath: bpy.props.StringProperty(name='Filepath', default='//Cache/', update=handler_update_filepath)
    use_cache: bpy.props.BoolProperty(name='Use Cache', default=False)
    modifier_visibility: bpy.props.CollectionProperty(type=ModifierVisibilitySettings, name='Modifier Visibility')
    
    
class MeshSourceSettings(bpy.types.PropertyGroup):
    enabled: bpy.props.BoolProperty(name='Enabled', default=False, update=handler_toggle_mesh_source)
    original_data: bpy.props.PointerProperty(type=bpy.types.Mesh, name='Original Data')
    source_object: bpy.props.PointerProperty(type=bpy.types.Object, name='Source Object', poll=filter_renderable_objects)
    use_modifiers: bpy.props.BoolProperty(name='Use Modifiers', default=False)


class ApplyModifierCache(bpy.types.Operator):
    """Toggle Modifier Cache"""
    bl_idname = "object.apply_modifier_cache"
    bl_label = "Apply Modifier Cache"
    
    def apply_modifier_cache(self, obj):
        if '__MODIFIER_SEQUENCE_CACHE__' in obj.modifiers:
            obj.modifiers['__MODIFIER_SEQUENCE_CACHE__'].name = 'Modifier Sequence Cache'
        obj.modifier_cache_settings.use_cache = False
        
                
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        self.apply_modifier_cache(context.object)
        return {'FINISHED'}


class FreeModifierCache(bpy.types.Operator):
    """Toggle Modifier Cache"""
    bl_idname = "object.free_modifier_cache"
    bl_label = "Free Modifier Cache"
    
    def disable_modifier_cache(self, obj):
        mcs = obj.modifier_cache_settings
        
        for mv in mcs.modifier_visibility:
            if mv.name in obj.modifiers:
                obj.modifiers[mv.name].show_viewport = mv.show_viewport
                obj.modifiers[mv.name].show_render = mv.show_render
        
        if '__MODIFIER_SEQUENCE_CACHE__' in obj.modifiers:
            obj.modifiers.remove(obj.modifiers['__MODIFIER_SEQUENCE_CACHE__'])
        
        mcs.use_cache = False
        
        return {'FINISHED'}
        
                
    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def execute(self, context):
        self.disable_modifier_cache(context.object)
        return {'FINISHED'}
    

class BakeModifierCache(bpy.types.Operator):
    """Bake Modifier Cache"""
    bl_idname = "object.bake_modifier_cache"
    bl_label = "Bake Modifier Cache"
    
    
    def setup(self, context):
        mcs = context.object.modifier_cache_settings
        context.scene.frame_set(mcs.frame_start)
        self.filepath = abspath(mcs.filepath)
        if not os.path.exists(self.filepath):
            os.makedirs(self.filepath)
        self._timer = context.window_manager.event_timer_add(0.000001, window=context.window)
        context.window_manager.modal_handler_add(self)
        context.window_manager.progress_begin(0, 9999)
        
    def cleanup(self, context):
        context.window_manager.progress_end()
        context.window_manager.event_timer_remove(self._timer)
        context.object.modifier_cache_settings.use_cache = True
        context.scene.frame_set(context.object.modifier_cache_settings.frame_start)
        self.enable_modifier_cache(context.object)
        
        
    def save_frame(self, context):
        obj = context.object
        fp = create_filepath(context.object.modifier_cache_settings.filepath, context.scene.frame_current)
        print(fp)
        bpy.ops.wm.alembic_export(filepath=fp,
            start=context.scene.frame_current,
            end=context.scene.frame_current+1,
            check_existing=False,
            selected=True,
            uvs=True,
            packuv=True,
            normals=True,
            vcolors=True,
            apply_subdiv=True,
            curves_as_mesh=False,
            as_background_job=False,
        )
        
            
    
    def set_cache_file(self, obj):
        mcs = obj.modifier_cache_settings
        
        cache_modifier = obj.modifiers.new('__MODIFIER_SEQUENCE_CACHE__', 'MESH_SEQUENCE_CACHE')
        
        fp = create_filepath(mcs.filepath, mcs.frame_start)
        print(fp)
        cachefile = None
        for cf in bpy.data.cache_files:
            if cf.filepath == fp:
                cachefile = cf
                break
            
        if cachefile == None:
            bpy.ops.cachefile.open(filepath=fp)
            cachefile = bpy.data.cache_files[-1]
            
        cache_modifier.cache_file = cachefile
        cache_modifier.cache_file.is_sequence = True
        cache_modifier.object_path = cache_modifier.cache_file.object_paths[0].path
        

    def enable_modifier_cache(self, obj):
        mcs = obj.modifier_cache_settings
        mv = mcs.modifier_visibility
        
        mv.clear()
        for modifier in obj.modifiers:
            print(modifier.name)
            new_mv = mv.add()
            new_mv.name = modifier.name
            new_mv.show_viewport = modifier.show_viewport
            modifier.show_viewport = False
            new_mv.show_render = modifier.show_render
            modifier.show_render = False
        
        self.set_cache_file(obj)
        
    def run(self, context):
        self.save_frame(context)
        context.window_manager.progress_update(context.scene.frame_current)
        context.scene.frame_set(context.scene.frame_current+1)
        if context.scene.frame_current > context.object.modifier_cache_settings.frame_end:
            self.cleanup(context)
            print('Finished')
            return {'FINISHED'}
        return {'RUNNING_MODAL'}
            

    @classmethod
    def poll(cls, context):
        return context.active_object is not None
    
    def modal(self, context, event):
        mcs = context.object.modifier_cache_settings
        if event.type == 'TIMER':
            return self.run(context)
                
        if event.type == 'ESC':
            self.cleanup(context)
            print('Cancelled')
            return {'CANCELLED'}
        
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.setup(context)
        return {'RUNNING_MODAL'}

class MeshSourcePanel(bpy.types.Panel):
    """Creates a Panel in the Modifier properties window"""
    bl_label = "Mesh Source"
    bl_idname = "MODIFIER_PT_mesh_source"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    bl_option = {'DEFAULT_CLOSED'}
        
    def draw_header(self, context):
        mss = context.object.mesh_source_settings
#        scene = context.scene
        layout = self.layout
        layout.prop(mss, "enabled", text="")


    def draw(self, context):
        obj = context.object
        mss = obj.mesh_source_settings
        mcs = obj.modifier_cache_settings
        layout = self.layout
        layout.enabled = mss.enabled and not mcs.use_cache

        row = layout.row()
        row.prop(mss, 'source_object')
        
        row = layout.row()
        row.prop(mss, 'use_modifiers')
        
        

class ModifierCachePanel(bpy.types.Panel):
    """Creates a Panel in the Modifier properties window"""
    bl_label = "Modifier Cache"
    bl_idname = "MODIFIER_PT_cache"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "modifier"
    bl_option = {'DEFAULT_CLOSED'}
        
    def draw(self, context):
        layout = self.layout
        obj = context.object
        mcs = obj.modifier_cache_settings

        row = layout.row()
        row.prop(mcs, 'frame_start')
        
        row = layout.row()
        row.prop(mcs, 'frame_end')
        
        
        row = layout.row()
        row.prop(mcs, "filepath")
        
        row = layout.row()
        row.label(text=create_filepath(mcs.filepath, mcs.frame_start))

        row = layout.row()
        if mcs.use_cache:
            row.operator("object.free_modifier_cache")
            row = layout.row()
            row.operator("object.apply_modifier_cache")
        else:
            row.operator("object.bake_modifier_cache")
        

    
def override_modifier_draw(self, context):
    layout = self.layout

    ob = context.object

    layout.operator_menu_enum("object.modifier_add", "type")

    for md in ob.modifiers:
        if md.name != '__MODIFIER_SEQUENCE_CACHE__':
            box = layout.template_modifier(md)
            
            if box:
                box.enabled = not ob.modifier_cache_settings.use_cache
                getattr(self, md.type)(box, ob, md)
                


def register():
    bpy.types.DATA_PT_modifiers._draw = bpy.types.DATA_PT_modifiers.draw
    bpy.types.DATA_PT_modifiers.draw = override_modifier_draw
    
    bpy.utils.register_class(ModifierVisibilitySettings)
    bpy.utils.register_class(ModifierCacheSettings)
    bpy.utils.register_class(MeshSourceSettings)
    bpy.utils.register_class(BakeModifierCache)
    bpy.utils.register_class(FreeModifierCache)
    bpy.utils.register_class(ApplyModifierCache)
    bpy.types.Object.modifier_cache_settings = bpy.props.PointerProperty(type=ModifierCacheSettings)
    bpy.types.Object.mesh_source_settings = bpy.props.PointerProperty(type=MeshSourceSettings)
    bpy.utils.register_class(MeshSourcePanel)
    bpy.utils.register_class(ModifierCachePanel)
    
    bpy.app.handlers.frame_change_post.append(handler_frame_update)
    bpy.app.handlers.depsgraph_update_post.append(handler_frame_update)


def unregister():
    bpy.types.DATA_PT_modifiers.draw = bpy.types.DATA_PT_modifiers._draw
    del bpy.types.Object.modifier_cache_settings
    del bpy.types.Object.mesh_source_settings
    bpy.utils.unregister_class(BakeModifierCache)
    bpy.utils.unregister_class(FreeModifierCache)
    bpy.utils.unregister_class(ApplyModifierCache)
    bpy.utils.unregister_class(ModifierVisibilitySettings)
    bpy.utils.unregister_class(ModifierCacheSettings)
    bpy.utils.unregister_class(MeshSourceSettings)
    bpy.utils.unregister_class(ModifierCachePanel)
    bpy.utils.unregister_class(MeshSourcePanel)
    
    bpy.app.handlers.frame_change_post.remove(handler_frame_update)
    bpy.app.handlers.depsgraph_update_post.remove(handler_frame_update)


if __name__ == "__main__":
    register()



