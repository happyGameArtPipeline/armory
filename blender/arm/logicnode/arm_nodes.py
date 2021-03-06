import bpy.types
from bpy.props import *
from nodeitems_utils import NodeItem

nodes = []
category_items = {}
category_items['Logic'] = []
category_items['Event'] = []
category_items['Action'] = []
category_items['Value'] = []
category_items['Variable'] = []
category_items['Input'] = []
category_items['Animation'] = []
category_items['Physics'] = []
category_items['Navmesh'] = []
category_items['Sound'] = []
category_items['Native'] = []

object_sockets = dict()
array_nodes = dict()

class ArmLogicTreeNode:
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'ArmLogicTreeType'

class ArmActionSocket(bpy.types.NodeSocket):
    bl_idname = 'ArmNodeSocketAction'
    bl_label = 'Action Socket'

    def draw(self, context, layout, node, text):
        layout.label(self.name)

    def draw_color(self, context, node):
        return (0.8, 0.3, 0.3, 1)

class ArmObjectSocket(bpy.types.NodeSocket):
    bl_idname = 'ArmNodeSocketObject'
    bl_label = 'Object Socket'
    default_value = StringProperty(name='Object', default='')

    def __init__(self):
        global object_sockets
        # Buckle up..
        # Match id strings to socket dict to retrieve socket in eyedropper operator
        object_sockets[str(id(self))] = self

    def draw(self, context, layout, node, text):
        if self.is_output:
            layout.label(self.name)
        elif self.is_linked:
            layout.label(self.name)
        else:
            row = layout.row(align=True)
            row.prop_search(self, 'default_value', bpy.context.scene, 'objects', icon='NONE', text='')
            op = row.operator('arm.node_eyedrop', text='', icon='EYEDROPPER', emboss=True)
            op.socket_index = str(id(self))

    def draw_color(self, context, node):
        return (0.15, 0.55, 0.75, 1)

class ArmNodeEyedropButton(bpy.types.Operator):
    '''Pick selected object'''
    bl_idname = 'arm.node_eyedrop'
    bl_label = 'Eyedrop'
    socket_index = StringProperty(name='Socket Index', default='')

    def execute(self, context):
        global object_sockets
        obj = bpy.context.active_object
        if obj != None:
            object_sockets[self.socket_index].default_value = obj.name
        return{'FINISHED'}

class ArmAnimActionSocket(bpy.types.NodeSocket):
    bl_idname = 'ArmNodeSocketAnimAction'
    bl_label = 'Action Socket'
    default_value = StringProperty(name='Action', default='')

    def draw(self, context, layout, node, text):
        if self.is_output:
            layout.label(self.name)
        elif self.is_linked:
            layout.label(self.name)
        else:
            layout.prop_search(self, 'default_value', bpy.data, 'actions', icon='NONE', text='')

    def draw_color(self, context, node):
        return (0.8, 0.8, 0.8, 1)

class ArmNodeAddInputButton(bpy.types.Operator):
    '''Add new input'''
    bl_idname = 'arm.node_add_input'
    bl_label = 'Add Input'
    node_index = StringProperty(name='Node Index', default='')
    socket_type = StringProperty(name='Socket Type', default='NodeSocketShader')

    def execute(self, context):
        global array_nodes
        inps = array_nodes[self.node_index].inputs
        inps.new(self.socket_type, 'Input ' + str(len(inps)))
        return{'FINISHED'}

class ArmNodeRemoveInputButton(bpy.types.Operator):
    '''Remove last input'''
    bl_idname = 'arm.node_remove_input'
    bl_label = 'Remove Input'
    node_index = StringProperty(name='Node Index', default='')

    def execute(self, context):
        global array_nodes
        inps = array_nodes[self.node_index].inputs
        if len(inps) > 0:
            inps.remove(inps.values()[-1])
        return{'FINISHED'}

class ArmNodeAddOutputButton(bpy.types.Operator):
    '''Add new output'''
    bl_idname = 'arm.node_add_output'
    bl_label = 'Add Output'
    node_index = StringProperty(name='Node Index', default='')
    socket_type = StringProperty(name='Socket Type', default='NodeSocketShader')

    def execute(self, context):
        global array_nodes
        outs = array_nodes[self.node_index].outputs
        outs.new(self.socket_type, 'Output ' + str(len(outs)))
        return{'FINISHED'}

class ArmNodeRemoveOutputButton(bpy.types.Operator):
    '''Remove last output'''
    bl_idname = 'arm.node_remove_output'
    bl_label = 'Remove Output'
    node_index = StringProperty(name='Node Index', default='')

    def execute(self, context):
        global array_nodes
        outs = array_nodes[self.node_index].outputs
        if len(outs) > 0:
            outs.remove(outs.values()[-1])
        return{'FINISHED'}

def add_node(node_class, category):
    global nodes
    nodes.append(node_class)
    category_items[category].append(NodeItem(node_class.bl_idname))

bpy.utils.register_class(ArmActionSocket)
bpy.utils.register_class(ArmObjectSocket)
bpy.utils.register_class(ArmNodeEyedropButton)
bpy.utils.register_class(ArmAnimActionSocket)
bpy.utils.register_class(ArmNodeAddInputButton)
bpy.utils.register_class(ArmNodeRemoveInputButton)
bpy.utils.register_class(ArmNodeAddOutputButton)
bpy.utils.register_class(ArmNodeRemoveOutputButton)
