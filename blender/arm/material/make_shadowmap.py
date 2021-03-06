import bpy
import arm.material.cycles as cycles
import arm.material.mat_state as mat_state
import arm.material.mat_utils as mat_utils
import arm.material.make_skin as make_skin
import arm.material.make_tess as make_tess
import arm.material.make_mesh as make_mesh
import arm.utils

def make(context_id, rpasses):

    is_disp = mat_utils.disp_linked(mat_state.output_node) and mat_state.material.arm_tess_shadows

    vs = [{'name': 'pos', 'size': 3}]
    if is_disp:
        vs.append({'name': 'nor', 'size': 3})

    con_shadowmap = mat_state.data.add_context({ 'name': context_id, 'vertex_structure': vs, 'depth_write': True, 'compare_mode': 'less', 'cull_mode': 'clockwise', 'color_write_red': False, 'color_write_green': False, 'color_write_blue': False, 'color_write_alpha': False })

    vert = con_shadowmap.make_vert()
    frag = con_shadowmap.make_frag()
    geom = None
    tesc = None
    tese = None

    gapi = arm.utils.get_gapi()
    if gapi == 'direct3d9':
        frag.add_out('vec4 fragColor') # Definition requred for d3d9 - pixel shader must minimally write all four components of COLOR0
    vert.write_main_header('vec4 spos = vec4(pos, 1.0);')

    parse_opacity = 'translucent' in rpasses or mat_state.material.arm_discard
    if parse_opacity:
        frag.write('vec3 n;') # Discard at compile time
        frag.write('float dotNV;')
        frag.write('float opacity;')

    if con_shadowmap.is_elem('bone'):
        make_skin.skin_pos(vert)

    if con_shadowmap.is_elem('off'):
        vert.write('spos.xyz += off;')

    if is_disp:
        tesc = con_shadowmap.make_tesc()
        tese = con_shadowmap.make_tese()
        tesc.ins = vert.outs
        tese.ins = tesc.outs
        frag.ins = tese.outs

        vert.add_out('vec3 wposition')
        vert.add_out('vec3 wnormal')
        vert.add_uniform('mat4 W', '_worldMatrix')
        vert.add_uniform('mat3 N', '_normalMatrix')
        vert.write('wnormal = normalize(N * nor);')
        vert.write('wposition = vec4(W * spos).xyz;')
        
        make_tess.tesc_levels(tesc, mat_state.material.arm_tess_shadows_inner, mat_state.material.arm_tess_shadows_outer)
        make_tess.interpolate(tese, 'wposition', 3)
        make_tess.interpolate(tese, 'wnormal', 3, normalize=True)

        cycles.parse(mat_state.nodes, con_shadowmap, vert, frag, geom, tesc, tese, parse_surface=False, parse_opacity=parse_opacity)

        if con_shadowmap.is_elem('tex'):
            vert.add_out('vec2 texCoord')
            vert.write('texCoord = tex;')
            tese.write_pre = True
            make_tess.interpolate(tese, 'texCoord', 2, declare_out=frag.contains('texCoord'))
            tese.write_pre = False

        if con_shadowmap.is_elem('tex1'):
            vert.add_out('vec2 texCoord1')
            vert.write('texCoord1 = tex1;')
            tese.write_pre = True
            make_tess.interpolate(tese, 'texCoord1', 2, declare_out=frag.contains('texCoord1'))
            tese.write_pre = False

        if con_shadowmap.is_elem('col'):
            vert.add_out('vec3 vcolor')
            vert.write('vcolor = col;')
            tese.write_pre = True
            make_tess.interpolate(tese, 'vcolor', 3, declare_out=frag.contains('vcolor'))
            tese.write_pre = False

        tese.add_uniform('mat4 LVP', '_lampViewProjectionMatrix')
        tese.write('wposition += wnormal * disp * 0.2;')
        tese.write('gl_Position = LVP * vec4(wposition, 1.0);')
    # No displacement
    else:
        frag.ins = vert.outs
        # billboard = mat_state.material.arm_billboard
        # if billboard == 'spherical':
        #     vert.add_uniform('mat4 LWVP', '_lampWorldViewProjectionMatrixSphere')
        # elif billboard == 'cylindrical':
        #     vert.add_uniform('mat4 LWVP', '_lampWorldViewProjectionMatrixCylinder')
        # else: # none
        vert.add_uniform('mat4 LWVP', '_lampWorldViewProjectionMatrix')
        vert.write('gl_Position = LWVP * spos;')

        if parse_opacity:
            cycles.parse(mat_state.nodes, con_shadowmap, vert, frag, geom, tesc, tese, parse_surface=False, parse_opacity=True)

            if con_shadowmap.is_elem('tex'):
                vert.add_out('vec2 texCoord')
                vert.write('texCoord = tex;')

            if con_shadowmap.is_elem('tex1'):
                vert.add_out('vec2 texCoord1')
                vert.write('texCoord1 = tex1;')

            if con_shadowmap.is_elem('col'):
                vert.add_out('vec3 vcolor')
                vert.write('vcolor = col;')
    
    # TODO: interleaved buffer has to match vertex structure of mesh context
    if not bpy.data.worlds['Arm'].arm_deinterleaved_buffers:
        con_shadowmap.add_elem('nor', 3)
        if mat_state.material.export_uvs:
            con_shadowmap.add_elem('tex', 2)

    # TODO: pass vbuf with proper struct
    if gapi.startswith('direct3d') and bpy.data.worlds['Arm'].arm_deinterleaved_buffers == False:
        vert.write('vec3 t1 = nor; // TODO: Temp for d3d')
        if con_shadowmap.is_elem('tex'):
            vert.write('vec2 t2 = tex; // TODO: Temp for d3d')

    if parse_opacity:
        opac = mat_state.material.arm_discard_opacity_shadows
        frag.write('if (opacity < {0}) discard;'.format(opac))

    # frag.write('fragColor = vec4(0.0);')

    make_mesh.make_finalize(con_shadowmap)

    return con_shadowmap
