"""Node materials. Wear and grime are procedural so a skin is a handful of numbers."""
import bpy
from .params import Skin


def _new(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def painted_metal(skin: Skin, name="hull_paint"):
    """Painted hull: base colour worn through to bare metal on edges and by noise,
    grime in the crevices, roughness broken up."""
    m, nt, out = _new(name)
    n = nt.nodes
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Metallic"].default_value = 0.3
    bsdf.inputs["Roughness"].default_value = 0.45
    bsdf.inputs["Coat Weight"].default_value = 0.35
    bsdf.inputs["Coat Roughness"].default_value = 0.15
    # wear mask: noise + pointiness-ish via ambient occlusion inverse
    tex = n.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 70.0; tex.inputs["Detail"].default_value = 8.0
    tex.inputs["Roughness"].default_value = 0.7
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.70 - 0.22 * skin.wear
    ramp.color_ramp.elements[1].position = 0.80 - 0.22 * skin.wear
    ao = n.new("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.02; ao.inside = True
    edge = n.new("ShaderNodeMath"); edge.operation = "MULTIPLY"
    invao = n.new("ShaderNodeMath"); invao.operation = "SUBTRACT"; invao.inputs[0].default_value = 1.0
    wearmix = n.new("ShaderNodeMath"); wearmix.operation = "MAXIMUM"
    base = n.new("ShaderNodeRGB"); base.outputs[0].default_value = (*skin.base, 1)
    bare = n.new("ShaderNodeRGB"); bare.outputs[0].default_value = (*skin.bare, 1)
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
    grime = n.new("ShaderNodeTexNoise"); grime.inputs["Scale"].default_value = 4.0; grime.inputs["Detail"].default_value = 8.0
    grimeramp = n.new("ShaderNodeValToRGB")
    grimeramp.color_ramp.elements[0].position = 0.45; grimeramp.color_ramp.elements[1].position = 0.7
    grimemix = n.new("ShaderNodeMix"); grimemix.data_type = "RGBA"
    grimemix.inputs["B"].default_value = (0.02, 0.018, 0.015, 1)
    grimefac = n.new("ShaderNodeMath"); grimefac.operation = "MULTIPLY"; grimefac.inputs[1].default_value = skin.grime
    rough = n.new("ShaderNodeMath"); rough.operation = "MULTIPLY_ADD"
    rough.inputs[1].default_value = 0.3; rough.inputs[2].default_value = 0.35
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.08
    L = nt.links.new
    L(tex.outputs["Fac"], ramp.inputs["Fac"])
    L(ao.outputs["AO"], invao.inputs[1])
    L(invao.outputs[0], edge.inputs[0]); edge.inputs[1].default_value = 4.0 * skin.wear
    L(ramp.outputs["Color"], wearmix.inputs[0]); L(edge.outputs[0], wearmix.inputs[1])
    L(wearmix.outputs[0], mix.inputs["Factor"])
    L(base.outputs[0], mix.inputs["A"]); L(bare.outputs[0], mix.inputs["B"])
    L(grime.outputs["Fac"], grimeramp.inputs["Fac"])
    L(grimeramp.outputs["Color"], grimefac.inputs[0])
    L(grimefac.outputs[0], grimemix.inputs["Factor"])
    L(mix.outputs["Result"], grimemix.inputs["A"])
    L(grimemix.outputs["Result"], bsdf.inputs["Base Color"])
    L(grime.outputs["Fac"], rough.inputs[0]); L(rough.outputs[0], bsdf.inputs["Roughness"])
    L(tex.outputs["Fac"], bump.inputs["Height"]); L(bump.outputs["Normal"], bsdf.inputs["Normal"])
    L(bsdf.outputs[0], out.inputs[0])
    return m


def accent(skin: Skin, name="accent_paint"):
    m, nt, out = _new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*skin.accent, 1)
    b.inputs["Metallic"].default_value = 0.3
    b.inputs["Roughness"].default_value = 0.55
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def bare_metal(name="bare_metal", tint=(0.6, 0.6, 0.62), rough=0.35):
    m, nt, out = _new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*tint, 1)
    b.inputs["Metallic"].default_value = 1.0
    b.inputs["Roughness"].default_value = rough
    tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 40
    r = nt.nodes.new("ShaderNodeMath"); r.operation = "MULTIPLY_ADD"; r.inputs[1].default_value = 0.25; r.inputs[2].default_value = rough - 0.1
    nt.links.new(tex.outputs["Fac"], r.inputs[0]); nt.links.new(r.outputs[0], b.inputs["Roughness"])
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def rubber(name="rubber"):
    m, nt, out = _new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.02, 0.02, 0.02, 1)
    b.inputs["Roughness"].default_value = 0.8
    b.inputs["Specular IOR Level"].default_value = 0.3
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def emissive(skin: Skin, name="light_strip", strength=None):
    m, nt, out = _new(name)
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*skin.light, 1)
    e.inputs["Strength"].default_value = strength if strength is not None else skin.light_strength
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def lens(name="lens"):
    m, nt, out = _new(name)
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (0.05, 0.08, 0.1, 1)
    b.inputs["Roughness"].default_value = 0.05
    b.inputs["Transmission Weight"].default_value = 0.6
    b.inputs["IOR"].default_value = 1.5
    nt.links.new(b.outputs[0], out.inputs[0])
    return m


def wet_rock(name="wet_rock"):
    """Cave floor and walls: dark, layered noise, wet sheen in the low spots."""
    m, nt, out = _new(name)
    n = nt.nodes
    b = n.new("ShaderNodeBsdfPrincipled")
    coord = n.new("ShaderNodeTexCoord")
    big = n.new("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 1.5; big.inputs["Detail"].default_value = 10; big.inputs["Roughness"].default_value = 0.65
    fine = n.new("ShaderNodeTexVoronoi"); fine.inputs["Scale"].default_value = 12
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (0.015, 0.014, 0.013, 1); ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[1].color = (0.11, 0.10, 0.09, 1); ramp.color_ramp.elements[1].position = 0.8
    b.inputs["Specular IOR Level"].default_value = 0.15
    wet = n.new("ShaderNodeValToRGB"); wet.color_ramp.elements[0].position = 0.2; wet.color_ramp.elements[1].position = 0.7
    rough = n.new("ShaderNodeMath"); rough.operation = "MULTIPLY_ADD"; rough.inputs[1].default_value = -0.2; rough.inputs[2].default_value = 0.95
    bump = n.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
    bump2 = n.new("ShaderNodeBump"); bump2.inputs["Strength"].default_value = 0.25
    L = nt.links.new
    L(coord.outputs["Object"], big.inputs["Vector"]); L(coord.outputs["Object"], fine.inputs["Vector"])
    L(big.outputs["Fac"], ramp.inputs["Fac"]); L(ramp.outputs["Color"], b.inputs["Base Color"])
    L(big.outputs["Fac"], wet.inputs["Fac"]); L(wet.outputs["Color"], rough.inputs[0]); L(rough.outputs[0], b.inputs["Roughness"])
    L(big.outputs["Fac"], bump.inputs["Height"]); L(fine.outputs["Distance"], bump2.inputs["Height"])
    L(bump2.outputs["Normal"], bump.inputs["Normal"]); L(bump.outputs["Normal"], b.inputs["Normal"])
    L(b.outputs[0], out.inputs[0])
    return m
