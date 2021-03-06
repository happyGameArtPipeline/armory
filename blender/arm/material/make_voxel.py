import bpy
import arm.utils
import arm.material.cycles as cycles
import arm.material.mat_state as mat_state
import arm.material.mat_utils as mat_utils

def make(context_id):
    rpdat = arm.utils.get_rp()
    if rpdat.rp_voxelgi:
        return make_gi(context_id)
    else:
        return make_ao(context_id)

def make_gi(context_id):
    con_voxel = mat_state.data.add_context({ 'name': context_id, 'depth_write': False, 'compare_mode': 'always', 'cull_mode': 'none', 'color_write_red': False, 'color_write_green': False, 'color_write_blue': False, 'color_write_alpha': False, 'conservative_raster': True })
    wrd = bpy.data.worlds['Arm']

    if '_NoShadows' in wrd.world_defs:
        is_shadows = False
    else:
        is_shadows = True

    vert = con_voxel.make_vert()
    frag = con_voxel.make_frag()
    geom = con_voxel.make_geom()
    tesc = None
    tese = None

    geom.ins = vert.outs
    frag.ins = geom.outs


    frag.write('vec3 lp = lightPos - wposition * voxelgiDimensions;')
    frag.write('vec3 l = normalize(lp);')
    frag.write('float visibility = 1.0;')
    frag.add_include('../../Shaders/compiled.glsl')
    if is_shadows:
        frag.add_include('../../Shaders/std/shadows.glsl')
        frag.add_uniform('sampler2D shadowMap', included=True)
        frag.add_uniform('samplerCube shadowMapCube', included=True)
        frag.add_uniform('int lightShadow', '_lampCastShadow')
        frag.add_uniform('vec2 lightPlane', '_lampPlane')
        frag.add_uniform('float shadowsBias', '_lampShadowsBias')
        frag.write('if (lightShadow == 1 && lampPos.w > 0.0) {')
        frag.write('    vec3 lpos = lampPos.xyz / lampPos.w;')
        frag.write('    if (texture(shadowMap, lpos.xy).r < lpos.z - shadowsBias) visibility = 0.0;')
        frag.write('}')
        frag.write('else if (lightShadow == 2) visibility = float(texture(shadowMapCube, -l).r + shadowsBias > lpToDepth(lp, lightPlane));')
    else:
        frag.write('int lightShadow = 0;')

    frag.add_include('../../Shaders/std/math.glsl')
    frag.add_include('../../Shaders/std/imageatomic.glsl')
    frag.write_header('#extension GL_ARB_shader_image_load_store : enable')

    rpdat = arm.utils.get_rp()
    # if rpdat.rp_voxelgi_hdr:
        # frag.add_uniform('layout(RGBA16) image3D voxels')
    # else:
    # frag.add_uniform('layout(RGBA8) image3D voxels')
    frag.add_uniform('layout(r32ui) uimage3D voxels')

    frag.add_uniform('vec3 lightPos', '_lampPosition')
    frag.add_uniform('vec3 lightColor', '_lampColorVoxel')

    frag.write('if (!isInsideCube(wposition)) return;')

    frag.write('vec3 basecol;')
    frag.write('float roughness;') #
    frag.write('float metallic;') #
    frag.write('float occlusion;') #
    parse_opacity = rpdat.arm_voxelgi_refraction
    if parse_opacity:
        frag.write('float opacity;')
    frag.write_pre = True
    frag.write('mat3 TBN;') # TODO: discard, parse basecolor only
    frag.write_pre = False
    frag.write('float dotNV = 0.0;')
    frag.write('float dotNL = max(dot(wnormal, l), 0.0);')
    cycles.parse(mat_state.nodes, con_voxel, vert, frag, geom, tesc, tese, parse_opacity=parse_opacity, parse_displacement=False)

    if not frag.contains('vec3 n ='):
        frag.write_pre = True
        frag.write('vec3 n;')
        frag.write_pre = False

    if rpdat.arm_voxelgi_camera:
        vert.add_uniform('vec3 eye', '_cameraPosition')
    vert.add_uniform('mat4 W', '_worldMatrix')
    vert.add_uniform('mat3 N', '_normalMatrix')

    vert.add_out('vec3 wpositionGeom')
    vert.add_out('vec3 wnormalGeom')

    vert.add_include('../../Shaders/compiled.glsl')

    if con_voxel.is_elem('tex'):
        vert.add_out('vec2 texCoordGeom')
        vert.write('texCoordGeom = tex;')

    if rpdat.arm_voxelgi_camera:
        vert.write('const float step = voxelgiDimensions / voxelgiResolution;') # TODO: Pass as uniform
        vert.write('vec3 eyeSnap = ivec3(eye / step) * step;') # TODO: Pass as uniform
        vert.write('wpositionGeom = (vec3(W * vec4(pos, 1.0)) - eyeSnap) / voxelgiDimensions;')
    else: 
        vert.write('wpositionGeom = vec3(W * vec4(pos, 1.0)) / voxelgiDimensions;')
    vert.write('wnormalGeom = normalize(N * nor);')
    vert.write('gl_Position = vec4(0.0, 0.0, 0.0, 1.0);')

    if is_shadows:
        vert.add_out('vec4 lampPosGeom')
        vert.add_uniform('mat4 LWVP', '_biasLampWorldViewProjectionMatrix')
        vert.write('lampPosGeom = LWVP * vec4(pos, 1.0);')

    geom.add_out('vec3 wposition')
    geom.add_out('vec3 wnormal')
    if is_shadows:
        geom.add_out('vec4 lampPos')
    if con_voxel.is_elem('tex'):
        geom.add_out('vec2 texCoord')

    geom.write('const vec3 p1 = wpositionGeom[1] - wpositionGeom[0];')
    geom.write('const vec3 p2 = wpositionGeom[2] - wpositionGeom[0];')
    geom.write('const vec3 p = abs(cross(p1, p2));')
    geom.write('for (uint i = 0; i < 3; ++i) {')
    geom.write('    wposition = wpositionGeom[i];')
    geom.write('    wnormal = wnormalGeom[i];')
    if is_shadows:
        geom.write('    lampPos = lampPosGeom[i];')
    if con_voxel.is_elem('tex'):
        geom.write('    texCoord = texCoordGeom[i];')
    geom.write('    if (p.z > p.x && p.z > p.y) {')
    geom.write('        gl_Position = vec4(wposition.x, wposition.y, 0.0, 1.0);')
    geom.write('    }')
    geom.write('    else if (p.x > p.y && p.x > p.z) {')
    geom.write('        gl_Position = vec4(wposition.y, wposition.z, 0.0, 1.0);')
    geom.write('    }')
    geom.write('    else {')
    geom.write('        gl_Position = vec4(wposition.x, wposition.z, 0.0, 1.0);')
    geom.write('    }')
    geom.write('    EmitVertex();')
    geom.write('}')
    geom.write('EndPrimitive();')

    if cycles.emission_found:
        frag.write('vec3 color = basecol;')
    else:
        frag.write('vec3 color = basecol * visibility * lightColor * dotNL * attenuate(distance(wposition * voxelgiDimensions, lightPos));')
    frag.write('vec3 voxel = wposition * 0.5 + vec3(0.5);')

    if rpdat.arm_material_model == 'Cycles':
        frag.write('color = min(color * 0.9, vec3(0.9)) + min(color / 200.0, 0.1);') # Higher range to allow emission

    # if rpdat.rp_voxelgi_hdr:
        # frag.write('imageStore(voxels, ivec3(voxelgiResolution * voxel), vec4(color, 1.0));')
    # else:
    frag.write('color = clamp(color, vec3(0.0), vec3(1.0));')
    
    # frag.write('uint val = convVec4ToRGBA8(vec4(color, 1.0) * 255);')
    # frag.write('imageAtomicMax(voxels, ivec3(voxelgiResolution * voxel), val);')
    
    # frag.write('imageStore(voxels, ivec3(voxelgiResolution * voxel), vec4(color, 1.0));')
    # frag.write('imageAtomicRGBA8Avg(voxels, ivec3(voxelgiResolution * voxel), vec4(color, 1.0));')
        
    frag.write('ivec3 coords = ivec3(voxelgiResolution * voxel);')
    if parse_opacity:
        frag.write('vec4 val = vec4(color, opacity);')
    else:
        frag.write('vec4 val = vec4(color, 1.0);')
    frag.write('val *= 255.0;')
    frag.write('uint newVal = encUnsignedNibble(convVec4ToRGBA8(val), 1);')
    frag.write('uint prevStoredVal = 0;')
    frag.write('uint currStoredVal;')
    # frag.write('int counter = 0;')
    # frag.write('while ((currStoredVal = imageAtomicCompSwap(voxels, coords, prevStoredVal, newVal)) != prevStoredVal && counter < 16) {')
    frag.write('while ((currStoredVal = imageAtomicCompSwap(voxels, coords, prevStoredVal, newVal)) != prevStoredVal) {')
    frag.write('    vec4 rval = convRGBA8ToVec4(currStoredVal & 0xFEFEFEFE);')
    frag.write('    uint n = decUnsignedNibble(currStoredVal);')
    frag.write('    rval = rval * n + val;')
    frag.write('    rval /= ++n;')
    frag.write('    rval = round(rval / 2) * 2;')
    frag.write('    newVal = encUnsignedNibble(convVec4ToRGBA8(rval), n);')
    frag.write('    prevStoredVal = currStoredVal;')
    # frag.write('    counter++;')
    frag.write('}')

    # frag.write('val.rgb *= 255.0f;')
    # frag.write('uint newVal = convVec4ToRGBA8(val);')
    # frag.write('uint prevStoredVal = 0;')
    # frag.write('uint curStoredVal;')
    # frag.write('while ((curStoredVal = imageAtomicCompSwap(voxels, coords, prevStoredVal, newVal)) != prevStoredVal) {')
    # frag.write('    prevStoredVal = curStoredVal;')
    # frag.write('    vec4 rval = convRGBA8ToVec4(curStoredVal);')
    # frag.write('    rval.xyz = (rval.xyz * rval.w);')
    # frag.write('    vec4 curValF = rval + val;')
    # frag.write('    curValF.xyz /= (curValF.w);')
    # frag.write('    newVal = convVec4ToRGBA8(curValF);')
    # frag.write('}')

    return con_voxel

def make_ao(context_id):
    con_voxel = mat_state.data.add_context({ 'name': context_id, 'depth_write': False, 'compare_mode': 'always', 'cull_mode': 'none', 'color_write_red': False, 'color_write_green': False, 'color_write_blue': False, 'color_write_alpha': False, 'conservative_raster': True })
    wrd = bpy.data.worlds['Arm']

    vert = con_voxel.make_vert()
    frag = con_voxel.make_frag()
    geom = con_voxel.make_geom()
    tesc = None
    tese = None

    geom.ins = vert.outs
    frag.ins = geom.outs

    frag.add_include('../../Shaders/compiled.glsl')
    frag.add_include('../../Shaders/std/math.glsl')
    frag.write_header('#extension GL_ARB_shader_image_load_store : enable')

    rpdat = arm.utils.get_rp()
    frag.add_uniform('layout(RGBA8) image3D voxels')
    # frag.add_uniform('layout(R8) image3D voxels')

    frag.write('if (!isInsideCube(wposition)) return;')

    if rpdat.arm_voxelgi_camera:
        vert.add_uniform('vec3 eye', '_cameraPosition')
    vert.add_uniform('mat4 W', '_worldMatrix')

    vert.add_out('vec3 wpositionGeom')

    vert.add_include('../../Shaders/compiled.glsl')
    vert.write('wpositionGeom = vec3(W * vec4(pos, 1.0)) / voxelgiDimensions;')
    vert.write('gl_Position = vec4(0.0, 0.0, 0.0, 1.0);')

    geom.add_out('vec3 wposition')
    geom.write('const vec3 p1 = wpositionGeom[1] - wpositionGeom[0];')
    geom.write('const vec3 p2 = wpositionGeom[2] - wpositionGeom[0];')
    geom.write('const vec3 p = abs(cross(p1, p2));')
    geom.write('for (uint i = 0; i < 3; ++i) {')
    geom.write('    wposition = wpositionGeom[i];')
    geom.write('    if (p.z > p.x && p.z > p.y) {')
    geom.write('        gl_Position = vec4(wposition.x, wposition.y, 0.0, 1.0);')
    geom.write('    }')
    geom.write('    else if (p.x > p.y && p.x > p.z) {')
    geom.write('        gl_Position = vec4(wposition.y, wposition.z, 0.0, 1.0);')
    geom.write('    }')
    geom.write('    else {')
    geom.write('        gl_Position = vec4(wposition.x, wposition.z, 0.0, 1.0);')
    geom.write('    }')
    geom.write('    EmitVertex();')
    geom.write('}')
    geom.write('EndPrimitive();')

    frag.write('vec3 voxel = wposition * 0.5 + vec3(0.5);')
    frag.write('imageStore(voxels, ivec3(voxelgiResolution * voxel), vec4(1.0));')

    return con_voxel
