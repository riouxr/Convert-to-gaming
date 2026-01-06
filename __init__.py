bl_info = {
    "name": "BB Convert to Gaming",
    "author": "Blender Bob, Claude.ai",
    "version": (2, 1, 1),
    "blender": (4, 2, 0),
    "location": "View3D > UI > Tool",
    "description": "Converts high-poly objects to low-poly for gaming",
    "category": "Object",
}

import bpy
import bmesh
import re
from math import radians, pi

# Collection names for high-poly and low-poly objects
HIGH_COLL = "High"
LOW_COLL = "Low"

# Constants for decimate and geometry operations
PLANAR_ANGLE_DEGREES = 0.5  # Angle threshold for planar face decimation
NGON_EDGE_THRESHOLD = 5     # Faces with more edges than this are considered ngons


def ensure_collection(name):
    """
    Ensure a collection exists in the scene, creating it if necessary.
    
    Args:
        name (str): Name of the collection to ensure exists
        
    Returns:
        bpy.types.Collection: The collection object
    """
    col = bpy.data.collections.get(name)
    if not col:
        col = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(col)
        print(f"Created collection '{name}'")
    return col


def select_only(obj):
    """
    Select only the specified object and make it active.
    Ensures object mode before selection.
    
    Args:
        obj (bpy.types.Object): Object to select
    """
    if bpy.context.view_layer.objects.active and bpy.context.view_layer.objects.active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def apply_modifier_safe(obj, mod_name):
    """
    Safely apply a modifier to an object with error handling.
    
    Args:
        obj (bpy.types.Object): Object containing the modifier
        mod_name (str): Name of the modifier to apply
        
    Returns:
        bool: True if successful, False otherwise
    """
    select_only(obj)
    try:
        bpy.ops.object.modifier_apply(modifier=mod_name)
        return True
    except Exception as e:
        print(f"Failed to apply modifier '{mod_name}' on '{obj.name}': {e}")
        return False


def remove_modifier_safe(obj, modifier):
    """
    Safely remove a modifier from an object with error handling.
    
    Args:
        obj (bpy.types.Object): Object containing the modifier
        modifier (bpy.types.Modifier): Modifier to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    mod_name = modifier.name
    try:
        obj.modifiers.remove(modifier)
        return True
    except Exception as e:
        print(f"Failed to remove modifier '{mod_name}' on '{obj.name}': {e}")
        return False


def process_low_prep(obj):
    """
    Prepare a low-poly object by removing/applying modifiers and adding decimate.
    
    Steps:
    1. Rename object with "_low" suffix (removing _high and Blender auto-numbering)
    2. Remove Subdivision Surface and Smooth modifiers
    3. Apply ALL remaining modifiers
    4. Add planar Decimate modifier
    
    Args:
        obj (bpy.types.Object): Object to prepare
    """
    # Remove Blender's auto-numbering suffix (e.g., .001, .002)
    name_without_number = re.sub(r'\.\d+$', '', obj.name)
    
    # Remove _high suffix if present
    if name_without_number.endswith("_high"):
        base_name = name_without_number[:-5]  # Remove "_high" (5 characters)
    else:
        base_name = name_without_number
    
    # Add _low suffix (only if not already present)
    if not base_name.endswith("_low"):
        obj.name = base_name + "_low"

    # Remove Subsurf and Smooth modifiers (these add polygons)
    for m in list(obj.modifiers):
        if m.type in {"SUBSURF", "SMOOTH"}:
            remove_modifier_safe(obj, m)

    # Apply ALL remaining modifiers to bake their effects
    for m in list(obj.modifiers):
        mod_name = m.name
        applied = apply_modifier_safe(obj, mod_name)
        if not applied:
            print(f"Could not apply modifier '{mod_name}' on '{obj.name}'")

    # Remove any existing Decimate modifiers
    for m in list(obj.modifiers):
        if m.type == 'DECIMATE':
            remove_modifier_safe(obj, m)

    # Add planar Decimate modifier to remove coplanar faces
    try:
        dec = obj.modifiers.new(name="DecimatePlanar", type="DECIMATE")
        dec.decimate_type = 'DISSOLVE'
        dec.angle_limit = radians(PLANAR_ANGLE_DEGREES)  # Convert degrees to radians
        dec.delimit = {'NORMAL'}  # Only dissolve faces with similar normals
    except Exception as e:
        print(f"Failed to add Decimate modifier on '{obj.name}': {e}")


def process_low_apply_decimate(obj):
    """
    Apply the planar Decimate modifier to finalize geometry reduction.
    
    Args:
        obj (bpy.types.Object): Object with Decimate modifier to apply
    """
    # Find and apply the DISSOLVE type decimate modifier
    for m in obj.modifiers:
        if m.type == 'DECIMATE' and m.decimate_type == 'DISSOLVE':
            apply_modifier_safe(obj, m.name)
            return
    
    print(f"No DISSOLVE decimate modifier found on '{obj.name}'")


def add_apply_weighted_normal(obj):
    """
    Add and apply Weighted Normal modifier for improved shading on low-poly geometry.
    
    Weighted normals help preserve the appearance of smooth surfaces
    even with reduced polygon counts.
    
    Args:
        obj (bpy.types.Object): Object to add weighted normals to
    """
    # Remove any existing Weighted Normal modifiers
    for m in list(obj.modifiers):
        if m.type == 'WEIGHTED_NORMAL':
            remove_modifier_safe(obj, m)

    # Add and apply fresh Weighted Normal modifier
    try:
        wn = obj.modifiers.new(name="WeightedNormal", type="WEIGHTED_NORMAL")
        wn.weight = 50  # Standard weight value
        wn.keep_sharp = True  # Preserve sharp edges
        apply_modifier_safe(obj, wn.name)
    except Exception as e:
        print(f"Failed to add Weighted Normal on '{obj.name}': {e}")


def edit_triangulate_to_quads(obj):
    """
    Optimize mesh topology by triangulating large ngons and converting tris to quads.
    
    Process:
    1. Find faces with more than NGON_EDGE_THRESHOLD edges (large ngons)
    2. Triangulate those faces for stability
    3. Convert all triangles back to quads where topology allows
    
    Args:
        obj (bpy.types.Object): Mesh object to optimize
    """
    if obj.type != 'MESH':
        return

    select_only(obj)
    try:
        bpy.ops.object.mode_set(mode='EDIT')
    except Exception as e:
        print(f"Failed to enter Edit mode for '{obj.name}': {e}")
        return

    bm = bmesh.from_edit_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    # Deselect all faces first
    for f in bm.faces:
        f.select = False

    # Select ngons with more than NGON_EDGE_THRESHOLD vertices
    ngons = [f for f in bm.faces if len(f.verts) > NGON_EDGE_THRESHOLD]
    for f in ngons:
        f.select = True

    bmesh.update_edit_mesh(obj.data)

    # Triangulate selected ngons using bmesh for stability
    bm = bmesh.from_edit_mesh(obj.data)
    sel_faces = [f for f in bm.faces if f.select]
    if sel_faces:
        try:
            bmesh.ops.triangulate(
                bm,
                faces=sel_faces,
                quad_method='BEAUTY',
                ngon_method='BEAUTY'
            )
        except Exception as e:
            print(f"Triangulation failed on '{obj.name}': {e}")

    bmesh.update_edit_mesh(obj.data)

    # Select all faces for tris to quads conversion
    try:
        bpy.ops.mesh.select_all(action='SELECT')
    except Exception as e:
        print(f"Failed to select all faces on '{obj.name}': {e}")

    # Convert triangles to quads where possible with relaxed thresholds
    # Using pi (180°) for both thresholds allows maximum quad conversion
    try:
        bpy.ops.mesh.tris_convert_to_quads(
            face_threshold=pi,      # Maximum angle difference between face normals
            shape_threshold=pi,     # Maximum shape angle for quad formation
            uvs=False,              # Ignore UV coordinates
            vcols=False,            # Ignore vertex colors
            seam=False,             # Ignore UV seams
            sharp=False,            # Ignore sharp edges
            materials=False         # Ignore material boundaries
        )
    except Exception as e:
        print(f"Tris to quads conversion failed on '{obj.name}': {e}")

    # Return to object mode
    try:
        bpy.ops.object.mode_set(mode='OBJECT')
    except Exception as e:
        print(f"Failed to exit Edit mode for '{obj.name}': {e}")


def add_high_suffix_main():
    """
    Add _high suffix to all objects in High collection.
    
    If object already ends with _high, it's skipped.
    Otherwise, _high is appended to the current name.
    """
    print("=== Add _high Suffix Started ===")
    
    # Get High collection
    high = bpy.data.collections.get(HIGH_COLL)
    if not high:
        print(f"ERROR: Collection '{HIGH_COLL}' not found. Please create a '{HIGH_COLL}' collection first.")
        return
    
    renamed_count = 0
    skipped_count = 0
    
    for obj in high.objects:
        original_name = obj.name
        
        # Skip if already ends with _high
        if obj.name.endswith("_high"):
            skipped_count += 1
            continue
        
        # Add _high suffix
        obj.name = obj.name + "_high"
        renamed_count += 1
        print(f"Renamed: '{original_name}' → '{obj.name}'")
    
    print(f"Renamed {renamed_count} object(s), skipped {skipped_count} (already had _high suffix)")
    print("=== Add _high Suffix Finished ===")


def convert_main():
    """
    Main function for Convert operation.
    
    Duplicates objects from High collection to Low collection,
    prepares modifiers for low-poly conversion, and hides High collection.
    """
    print("=== Convert Started ===")
    
    # Get High collection
    high = bpy.data.collections.get(HIGH_COLL)
    if not high:
        print(f"ERROR: Collection '{HIGH_COLL}' not found. Please create a '{HIGH_COLL}' collection with your high-poly objects.")
        return

    # Ensure Low collection exists
    low = ensure_collection(LOW_COLL)

    # Duplicate objects from High to Low
    new_objects = []
    for src in high.objects:
        try:
            new_obj = src.copy()
            if src.data:
                try:
                    new_obj.data = src.data.copy()
                except Exception:
                    new_obj.data = src.data
            low.objects.link(new_obj)
            new_objects.append(new_obj)
        except Exception as e:
            print(f"Failed to duplicate '{src.name}': {e}")

    print(f"Duplicated {len(new_objects)} object(s) to '{LOW_COLL}' collection")

    # Prepare modifiers on Low objects
    for obj in new_objects:
        process_low_prep(obj)

    # Hide High collection
    try:
        high.hide_viewport = True
    except Exception as e:
        print(f"Failed to hide '{HIGH_COLL}' collection: {e}")

    print("=== Convert Finished ===")


def fix_ngons_main():
    """
    Main function for Fix nGones operation.
    
    Applies decimate modifier, optimizes mesh topology,
    and adds weighted normals to all objects in Low collection.
    """
    print("=== Fix nGones Started ===")
    
    # Get Low collection
    low = bpy.data.collections.get(LOW_COLL)
    if not low:
        print(f"ERROR: Collection '{LOW_COLL}' not found. Run 'Convert' first.")
        return

    low_objects = [obj for obj in low.objects if obj.type == 'MESH']
    print(f"Processing {len(low_objects)} mesh object(s) in '{LOW_COLL}' collection")

    # Apply decimate modifier
    for obj in low_objects:
        process_low_apply_decimate(obj)

    # Optimize geometry topology
    for obj in low_objects:
        edit_triangulate_to_quads(obj)

    # Add weighted normals for better shading
    for obj in low_objects:
        add_apply_weighted_normal(obj)

    print("=== Fix nGones Finished ===")


class AddHighSuffixOperator(bpy.types.Operator):
    """Add _high suffix to all objects in High collection"""
    bl_idname = "object.add_high_suffix"
    bl_label = "Add _High Suffix"
    bl_description = "Add _high suffix to all objects in High collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        add_high_suffix_main()
        return {'FINISHED'}


class ConvertOperator(bpy.types.Operator):
    """Duplicate and prepare low-poly objects from High collection"""
    bl_idname = "object.convert_to_gaming"
    bl_label = "Convert"
    bl_description = "Duplicate objects from High collection, prep for low-poly, and hide High collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        convert_main()
        return {'FINISHED'}


class FixNgonsOperator(bpy.types.Operator):
    """Finalize low-poly geometry with decimate, topology optimization, and weighted normals"""
    bl_idname = "object.fix_ngons"
    bl_label = "Fix nGones"
    bl_description = "Apply dissolve decimate, optimize topology, and add weighted normals to Low collection objects"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        fix_ngons_main()
        return {'FINISHED'}


class ConvertToGamingPanel(bpy.types.Panel):
    """Panel in the 3D Viewport sidebar for Convert to Gaming addon"""
    bl_label = "BB Convert to Gaming"
    bl_idname = "VIEW3D_PT_convert_to_gaming"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Tool"

    def draw(self, context):
        layout = self.layout
        
        # Instructions
        box = layout.box()
        box.label(text="1. Put high-poly objects in 'High' collection", icon='INFO')
        box.label(text="2. Click 'Convert' to create low-poly versions")
        box.label(text="3. Adjust Decimate Angle Limit if needed")
        box.label(text="4. Click 'Fix nGones' to finalize geometry")
        
        layout.separator()
        
        # Main buttons
        layout.operator(AddHighSuffixOperator.bl_idname, icon='SORTALPHA')
        layout.operator(ConvertOperator.bl_idname, icon='DUPLICATE')
        layout.operator(FixNgonsOperator.bl_idname, icon='MOD_DECIM')


def register():
    """Register addon classes with Blender"""
    bpy.utils.register_class(AddHighSuffixOperator)
    bpy.utils.register_class(ConvertOperator)
    bpy.utils.register_class(FixNgonsOperator)
    bpy.utils.register_class(ConvertToGamingPanel)


def unregister():
    """Unregister addon classes from Blender"""
    bpy.utils.unregister_class(ConvertToGamingPanel)
    bpy.utils.unregister_class(FixNgonsOperator)
    bpy.utils.unregister_class(ConvertOperator)
    bpy.utils.unregister_class(AddHighSuffixOperator)


if __name__ == "__main__":
    register()
