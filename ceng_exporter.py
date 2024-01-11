bl_info = {
    "name": "Ceng Raytracer Format Exporter",
    "author": "Akif Uslu",
    "version": (1, 0),
    "blender": (3, 6, 0),
    "location": "",
    "description": "Exports ceng raytracer .xml format",
    "warning": "",
    "doc_url": "",
    "category": "Export",
}


import bpy
import math
import copy
from mathutils import Vector
import xml.etree.ElementTree as ET
import bmesh
import os


def get_mesh_data(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.split(bm, geom=bm.verts[:])
    print(len(bm.verts))
    print(len(bm.faces))

    verts = []
    uvs = []
    faces = []
    k = 0
    uv_lay = bm.loops.layers.uv.active    
    for face in bm.faces:
        fc = []
        for loop in face.loops:
            uv = loop[uv_lay].uv
            uvs.append(uv[:])
            vert = loop.vert
            verts.append(vert.co[:])
            fc.append(k)
            k += 1
        faces.append(fc)
    bm.free()
    return verts, uvs, faces

def calculate_near_plane(camera):
    camera_data = camera.data
    fov = camera_data.angle
    width = bpy.data.scenes[0].render.resolution_x
    height = bpy.data.scenes[0].render.resolution_y
    near_plane_distance = 0.5 * camera_data.clip_start / math.tan(fov / 2)
    aspect_ratio = width / height
    half_near_width = near_plane_distance * math.tan(fov / 2)
    near_bounds = (
        -half_near_width,  # left
        half_near_width,   # right
        -half_near_width / aspect_ratio,  # bottom
        half_near_width / aspect_ratio    # top
    )

    return near_plane_distance, near_bounds

def export(context, filepath):    
    dirpath = os.path.dirname(filepath)
    texpath = os.path.join(dirpath, 'textures')
    if not os.path.exists(texpath):
        os.makedirs(texpath)

    depsgraph = context.evaluated_depsgraph_get()
    scene = ET.Element('Scene')
    back_color = ET.SubElement(scene, 'BackgroundColor')
    shadow_ray_eps = ET.SubElement(scene, 'ShadowRayEpsilon')
    max_recursion = ET.SubElement(scene, 'MaxRecursionDepth')
    cameras = ET.SubElement(scene, 'Cameras')
    lights = ET.SubElement(scene, 'Lights')
    materials = ET.SubElement(scene, 'Materials')
    textures = ET.SubElement(scene, 'Textures')
    vertex_data = ET.SubElement(scene, 'VertexData')
    texcoord_data = ET.SubElement(scene, 'TexCoordData')

    objects = ET.SubElement(scene, 'Objects')

    b_color = list(bpy.data.worlds['World'].node_tree.nodes["Background"].inputs[0].default_value)
    b_color[0] = int(b_color[0] * 255);
    b_color[1] = int(b_color[1] * 255);
    b_color[2] = int(b_color[2] * 255);
    ambient = ET.SubElement(lights, 'AmbientLight')
    ambient.text = '0 0 0'
    back_color.text = str(b_color[0]) + ' ' + str(b_color[1]) + ' ' + str(b_color[2])
    shadow_ray_eps.text = '1e-3'
    max_recursion.text = '6'

    mat_tex_dict = {}
    mat_id = 1
    tex_id = 1
    for mat in bpy.data.materials:
        m = ET.SubElement(materials, 'Material')
        m.set('id', str(mat_id))
        mat_id += 1
        if mat.use_nodes == False or mat.node_tree.nodes.find('Principled BSDF') == -1:
            ET.SubElement(m, 'AmbientReflectance').text = '0 0 0'
            ET.SubElement(m, 'DiffuseReflectance').text = '0 0 0'
            ET.SubElement(m, 'SpecularReflectance').text = '0 0 0'
            ET.SubElement(m, 'MirrorReflectance').text = '0 0 0'
            ET.SubElement(m, 'PhongExponent').text = '1'
            continue # nodes and principled bsdf only, but we need to fill it as empty for indexing purposes
        
        amb = ET.SubElement(m, 'AmbientReflectance')
        amb.text = '1 1 1' # blender doesnt have such a thing afaik
        dif = ET.SubElement(m, 'DiffuseReflectance')
        dif_c = mat.node_tree.nodes['Principled BSDF'].inputs[0].default_value
        dif.text = str(dif_c[0]) + ' ' + str(dif_c[1]) + ' ' + str(dif_c[2])
        spec = ET.SubElement(m, 'SpecularReflectance')
        spe_c = mat.node_tree.nodes['Principled BSDF'].inputs[7].default_value
        spec.text = str(spe_c) + ' ' + str(spe_c) + ' ' + str(spe_c)
        mir = ET.SubElement(m, 'MirrorReflectance')
        mir_c = 1 - mat.node_tree.nodes['Principled BSDF'].inputs[9].default_value
        mir.text = str(mir_c) + ' ' + str(mir_c) + ' ' + str(mir_c)
        phong = ET.SubElement(m, 'PhongExponent')
        phong.text = '1' # NA
        
        for node in mat.node_tree.nodes:
            if node.type != 'TEX_IMAGE':
                continue
            tex = node.image
            tex_name = os.path.splitext(tex.name)[0] + '.jpg'
            t_path = os.path.join(texpath, tex_name)
            sc=context.scene
            sc.render.image_settings.file_format='JPEG'
            tex.save_render(t_path, scene = sc)
            t = ET.SubElement(textures, 'Texture')
            t.set('id', str(tex_id))
            mat_tex_dict[mat_id - 1] = tex_id
            tex_id += 1        
            path = ET.SubElement(t, 'ImageName')
            path.text = os.path.join('textures', tex_name)
            interp = ET.SubElement(t, 'Interpolation')
            interp.text = 'nearest' if node.interpolation == 'Closest' else 'bilinear'
            decal = ET.SubElement(t, 'DecalMode')
            decal.text = 'replace_kd'        
            app = ET.SubElement(t, 'Appearance')
            app.text = 'repeat' if node.extension == 'REPEAT' else 'clamp'



    print(mat_tex_dict)
    cam_id = 1
    light_id = 1
    mesh_id = 1
    face_offset = 0
    verts = ''
    uvs = ''
    for obj in bpy.context.view_layer.objects:
        if obj.type == 'CAMERA':
            cam = ET.SubElement(cameras, 'Camera')
            cam.set('id', str(cam_id))
            cam_id += 1
            campos = ET.SubElement(cam, 'Position')
            campos.text = str(obj.location[0]) + ' ' + str(obj.location[1]) + ' ' + str(obj.location[2])
            gaze = ET.SubElement(cam, 'Gaze')
            c_gaze = obj.matrix_world.to_quaternion() @ Vector((0.0, 0.0, -1.0))
            gaze.text = str(c_gaze[0]) + ' ' + str(c_gaze[1]) + ' ' + str(c_gaze[2])
            up = ET.SubElement(cam, 'Up')
            c_up = obj.matrix_world.to_quaternion() @ Vector((0.0, 1.0, 0.0))
            up.text = str(c_up[0]) + ' ' + str(c_up[1]) + ' ' + str(c_up[2])
            render = bpy.data.scenes['Scene'].render

            n_dist, n_bounds = calculate_near_plane(obj)
            near_plane = ET.SubElement(cam, 'NearPlane')       
            near_plane.text = str(n_bounds[0]) + ' ' + str(n_bounds[1]) + ' ' + str(n_bounds[2]) + ' ' + str(n_bounds[3])
            near_dist = ET.SubElement(cam, 'NearDistance')
            near_dist.text = str(n_dist)


            res = ET.SubElement(cam, 'ImageResolution')
            res.text = str(render.resolution_x) + ' ' + str(render.resolution_y)
            im_name = ET.SubElement(cam, 'ImageName')
            im_name.text = obj.name + '.jpg'
        elif obj.type == 'LIGHT':
            light = ET.SubElement(lights, 'PointLight')
            light.set('id', str(light_id))
            light_id += 1
            lpos = ET.SubElement(light, 'Position')
            lpos.text = str(obj.location[0]) + ' ' + str(obj.location[1]) + ' ' + str(obj.location[2])
            lint = ET.SubElement(light, 'Intensity')
            b_l_i = list(obj.data.color)
            b_l_i[0] *= obj.data.energy
            b_l_i[1] *= obj.data.energy
            b_l_i[2] *= obj.data.energy
            lint.text = str(b_l_i[0]) + ' ' + str(b_l_i[1]) + ' ' + str(b_l_i[2])
        elif obj.type == 'MESH':            
            if obj.active_material is None:
                continue

            object_eval = obj.evaluated_get(depsgraph)
            mesh_from_eval = object_eval.to_mesh()
            mesh_from_eval.transform(object_eval.matrix_world)            
            v_data, uv_data, f_data = get_mesh_data(mesh_from_eval)
            object_eval.to_mesh_clear()
            

            for v in v_data:
                verts += str(v[0]) + ' ' + str(v[1]) + ' ' + str(v[2]) + ' '

            for uv in uv_data:
                uvs += str(uv[0]) + ' ' + str(1-uv[1]) + ' '

            mesh = ET.SubElement(objects, 'Mesh')
            mesh.set('id', str(mesh_id))
            mesh_id += 1
            mat = ET.SubElement(mesh, 'Material')
            mat_ind = bpy.data.materials.find(obj.active_material.name) + 1
            mat.text = str(mat_ind)
            if mat_ind in mat_tex_dict:                
                tex = ET.SubElement(mesh, 'Texture')
                tex.text = str(mat_tex_dict[mat_ind])

            faces = ET.SubElement(mesh, 'Faces')
            f_t = ''
            for f in f_data:
                f_t += str(face_offset + f[0] + 1) + ' ' + str(face_offset + f[1] + 1) + ' ' + str(face_offset + f[2] + 1) + ' '
            faces.text = f_t
            face_offset += len(f_data * 3)  
            
    vertex_data.text = verts
    texcoord_data.text = uvs
    exp = ET.tostring(scene).decode()
    fl = open(filepath, 'w')
    fl.write(exp)
    return {'FINISHED'}


#path = '/Users/revelgames/Downloads/Assignment2_all_in_one/hw2_sample_scenes/'
#export(bpy.context, path)


from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ExportCengRaytracer(Operator, ExportHelper):
    """Export CengRaytracer format"""
    bl_idname = "export_cengraytracer.format"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Export CengRaytracer"

    # ExportHelper mixin class uses this
    filename_ext = ".xml"

    filter_glob: StringProperty(
        default="*.xml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        return export(context, self.filepath)


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(ExportCengRaytracer.bl_idname, text="CengRaytracer")


def register():
    bpy.utils.register_class(ExportCengRaytracer)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(ExportCengRaytracer)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()
