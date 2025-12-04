from agentkernel_standalone.toolkit.models.api.openai import OpenAIProvider
from agentkernel_standalone.mas.system.components import Messager, Recorder, Timer
from agentkernel_standalone.mas.action.components import CommunicationComponent
from agentkernel_standalone.mas.agent.components import *
from agentkernel_standalone.mas.environment.components import RelationComponent, SpaceComponent
from examples.standalone_test.custom_controller import CustomController

from examples.standalone_test.plugins.agent.invoke.EasyInvokePlugin import EasyInvokePlugin
from examples.standalone_test.plugins.agent.perceive.EasyPerceivePlugin import EasyPerceivePlugin
from examples.standalone_test.plugins.agent.profile.EasyProfilePlugin import EasyProfilePlugin
from examples.standalone_test.plugins.agent.state.EasyStatePlugin import EasyStatePlugin
from examples.standalone_test.plugins.agent.plan.EasyPlanPlugin import EasyPlanPlugin
from examples.standalone_test.plugins.agent.reflect.EasyReflectPlugin import EasyReflectPlugin

from examples.standalone_test.plugins.action.communication.EasyCommunicationPlugin import EasyCommunicationPlugin
from examples.standalone_test.plugins.environment.relation.EasyRelationPlugin import EasyRelationPlugin
from examples.standalone_test.plugins.environment.space.EasySpacePlugin import EasySpacePlugin

# Agent plugin and component registry

agent_plugin_calss_map = {
    "EasyPerceivePlugin": EasyPerceivePlugin,
    "EasyProfilePlugin": EasyProfilePlugin,
    "EasyStatePlugin": EasyStatePlugin,
    "EasyPlanPlugin": EasyPlanPlugin,
    "EasyInvokePlugin": EasyInvokePlugin,
    "EasyReflectPlugin": EasyReflectPlugin,
}

agent_component_class_map = {
    "profile": ProfileComponent,
    "state": StateComponent,
    "plan": PlanComponent,
    "perceive": PerceiveComponent,
    "reflect": ReflectComponent,
    "invoke": InvokeComponent,
}

# Action plugin and component registry
action_component_class_map = {
    "communication": CommunicationComponent,
}
action_plugin_class_map = {
    "EasyCommunicationPlugin": EasyCommunicationPlugin,
}
# Model class
model_class_map = {
    "OpenAIProvider": OpenAIProvider,
}
# Environment plugin and component registry
environment_component_class_map = {
    "relation": RelationComponent,
    "space": SpaceComponent,
}
environment_plugin_class_map = {
    "EasyRelationPlugin": EasyRelationPlugin,
    "EasySpacePlugin": EasySpacePlugin,
}

system_component_class_map = {
    "messager": Messager,
    "recorder": Recorder,
    "timer": Timer,
}

RESOURCES_MAPS = {
    "agent_components": agent_component_class_map,
    "agent_plugins": agent_plugin_calss_map,
    "action_components": action_component_class_map,
    "action_plugins": action_plugin_class_map,
    "environment_components": environment_component_class_map,
    "environment_plugins": environment_plugin_class_map,
    "system_components": system_component_class_map,
    "models": model_class_map,
    "controller": CustomController,
}
