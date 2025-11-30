"""Abstract base class defining the pod manager interface."""

import abc
from typing import Any, Dict, Optional, Type
from ray.actor import ActorHandle

from ...toolkit.models.router import ModelRouter
from ...toolkit.storages.base import DatabaseAdapter
from ...types.configs import Config
from ...types.schemas.message import Message
from ..controller import BaseController, Controller
from .mas_pod import MasPod
from ..system.system import System


class BasePodManager(abc.ABC):
    """Declare the lifecycle hooks and responsibilities of pod managers."""

    def __init__(
        self,
        pod_size: int = 5,
        init_batch_size: int = 5,
        controller_class: Optional[Type[BaseController]] = None,
    ) -> None:
        """
        Initialize common pod manager state.

        Args:
            pod_size (int): Maximum number of agents per pod. Default is 5.
            init_batch_size (int): Number of pods to initialize concurrently. Default is 5.
            controller_class (Optional[Type[BaseController]]): Controller implementation used by pods.
        """
        self._pod_size = pod_size
        self._init_batch_size = init_batch_size
        self._controller_class = controller_class if controller_class is not None else Controller

        self._pod_id_to_pod: Dict[str, MasPod] = {}
        self._agent_id_to_pod: Dict[str, MasPod] = {}

        self._configs: Optional[Config] = None
        self._resource_maps: Dict[str, Dict[str, Any]] = {}
        self._model_router: Optional[ModelRouter] = None
        self._system_handle: Optional[System] = None

        self._connection_pools: Dict[str, Any] = {}
        self._adapters: Dict[str, DatabaseAdapter] = {}

    @abc.abstractmethod
    async def init(
        self, configs: Config, resource_maps: Dict[str, Dict[str, Any]], model_router: Optional[ModelRouter] = None
    ) -> None:
        """
        Perform the first-stage initialization by creating pods.

        Args:
            configs (Config): Global configuration object for the MAS deployment.
            resource_maps (Dict[str, Dict[str, Any]]): Mapping of resource categories to their implementations.
            model_router (Optional[ModelRouter]): Optional model router shared across pods.
        """

    @abc.abstractmethod
    async def post_init(self, system_handle: "System", pod_manager_handle: ActorHandle) -> None:
        """
        Distribute shared dependencies to pods after initial construction.

        Args:
            system_handle ("System"): System service interface.
            pod_manager_handle (ActorHandle): Handle to the pod manager itself (local or remote).
        """

    @abc.abstractmethod
    async def step_agent(self) -> None:
        """Advance every agent under management by one simulation step."""

    @abc.abstractmethod
    async def deliver_message(self, to_id: str, message: Message) -> bool:
        """
        Deliver a message to an agent.

        Args:
            to_id (str): Target agent identifier.
            message (Message): Message payload destined for the agent.

        Returns:
            bool: True when the message is delivered successfully.
        """

    @abc.abstractmethod
    async def run_agent_method(
        self, agent_id: str, component_name: str, method_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """
        Execute a component method on a specific agent.

        Args:
            agent_id (str): Identifier of the target agent.
            component_name (str): Component that exposes the method.
            method_name (str): Name of the method to execute.
            *args (Any): Positional arguments forwarded to the method.
            **kwargs (Any): Keyword arguments forwarded to the method.

        Returns:
            Any: Result produced by the agent method.
        """

    @abc.abstractmethod
    async def add_agent(self, agent_id: str, template_name: str, data: Dict[str, Any]) -> bool:
        """
        Add a new agent to the managed population.

        Args:
            agent_id (str): Identifier for the new agent.
            template_name (str): Agent template used for instantiation.
            data (Dict[str, Any]): Initialization payload for the agent.

        Returns:
            bool: True when the agent is added successfully.
        """

    @abc.abstractmethod
    async def remove_agent(self, agent_id: str) -> bool:
        """
        Remove an agent from the managed population.

        Args:
            agent_id (str): Identifier of the agent to remove.

        Returns:
            bool: True when the agent is removed successfully.
        """

    @abc.abstractmethod
    async def make_snapshot(self) -> bool:
        """
        Trigger snapshot creation across all pods.

        Returns:
            bool: True when snapshot creation succeeds.
        """

    @abc.abstractmethod
    async def rollback_to_tick(self, tick: int) -> bool:
        """
        Roll pods back to a previous simulation tick.

        Args:
            tick (int): Simulation tick to restore.

        Returns:
            bool: True when the rollback succeeds.
        """

    @abc.abstractmethod
    async def close(self) -> bool:
        """
        Release resources allocated by the pod manager.

        Returns:
            bool: True when resources were released successfully.
        """
