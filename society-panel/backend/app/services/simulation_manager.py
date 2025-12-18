"""
Service for managing simulation lifecycle and execution.
"""

import asyncio
import os
import sys
import time
from enum import Enum
from typing import Any, Dict, Optional
import ray
from datetime import datetime

from agentkernel_distributed.mas.builder import Builder
from agentkernel_distributed.mas.pod import BasePodManager
from agentkernel_distributed.mas.system import System
from agentkernel_distributed.types.schemas import Message


class SimulationStatus(str, Enum):
    """Enumeration of possible simulation states."""
    STOPPED = "stopped"
    RUNNING = "running"
    STARTING = "starting"
    STOPPING = "stopping"
    ERROR = "error"


class SimulationManager:
    """
    A singleton service for managing the entire simulation lifecycle.
    """

    def __init__(self):
        """
        Initialize the SimulationManager with default state and workspace configuration.
        """
        self._status: SimulationStatus = SimulationStatus.STOPPED
        self._simulation_task: Optional[asyncio.Task] = None
        self._builder: Optional[Builder] = None
        self._pod_manager: Optional[BasePodManager] = None
        self._system: Optional[System] = None
        self._error_message: Optional[str] = None

        self.workspace_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "workspace"))
        os.makedirs(self.workspace_path, exist_ok=True)

        self.decoupling_output_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "decoupling_output")
        )

        if "MAS_PROJECT_ABS_PATH" not in os.environ:
            os.environ["MAS_PROJECT_ABS_PATH"] = self.workspace_path

        print(f"SimulationManager initialized. Workspace: {self.workspace_path}")

    @property
    def status(self) -> Dict[str, Any]:
        """
        Get the current simulation status.

        Returns:
            Dict[str, Any]: A dictionary containing status and error information.
        """
        return {"status": self._status, "error": self._error_message}

    async def start_simulation(self):
        """
        Start the simulation main entry point.

        Returns:
            dict: The current simulation status.
        """
        if self._status in [SimulationStatus.RUNNING, SimulationStatus.STARTING]:
            print("Simulation is already running or starting.")
            return self.status

        self._status = SimulationStatus.STARTING
        self._error_message = None
        print("Attempting to start simulation...")

        await self.cleanup()

        self._simulation_task = asyncio.create_task(self._run_simulation_loop())

        await asyncio.sleep(1)

        if self._status == SimulationStatus.ERROR:
            print("Simulation failed during startup.")
        elif self._status == SimulationStatus.STARTING:
            self._status = SimulationStatus.RUNNING
            print("Simulation has been started and is now running in the background.")

        return self.status

    async def _run_simulation_loop(self):
        """
        Execute the core simulation loop.
        """
        try:
            if not ray.is_initialized():
                backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
                current_pythonpath = os.environ.get("PYTHONPATH", "")
                new_pythonpath = f"{backend_dir}{os.pathsep}{current_pythonpath}"

                runtime_env = {
                    "working_dir": self.workspace_path,
                    "env_vars": {
                        "PYTHONPATH": new_pythonpath,
                    },
                    "excludes": [
                        os.path.join(backend_dir, ".venv"),
                        "*.pyc",
                        "__pycache__",
                        ".git",
                        ".idea",
                        "decoupling_output",
                    ],
                }
                print(f"Initializing Ray with runtime_env: {runtime_env}")
                ray.init(runtime_env=runtime_env)

            if self.workspace_path not in sys.path:
                sys.path.insert(0, self.workspace_path)

            try:
                import importlib

                if "registry" in sys.modules:
                    importlib.reload(sys.modules["registry"])
                from registry import RESOURCE_MAPS
            except (ImportError, FileNotFoundError) as e:
                raise RuntimeError(f"Failed to load registry: {e}")

            self._builder = Builder(project_path=self.workspace_path, resource_maps=RESOURCE_MAPS)

            self._pod_manager, self._system = await self._builder.init()

            print("--- Simulation components initialized ---")

            max_ticks = self._builder.config.simulation.max_ticks
            print(f"--- Starting Simulation Run for {max_ticks} ticks ---")

            self._status = SimulationStatus.RUNNING

            for i in range(max_ticks):
                if self._status != SimulationStatus.RUNNING:
                    print(f"Simulation status changed to '{self._status}'. Exiting simulation loop.")
                    break

                tick_start_time = time.time()

                await self._pod_manager.step_agent.remote()
                await self._system.run("messager", "dispatch_messages")
                await self._pod_manager.update_agents_status.remote()

                tick_end_time = time.time()
                actual_tick_duration = tick_end_time - tick_start_time
                current_tick = await self._system.run("timer", "get_tick")
                await self._system.run("timer", "add_tick", duration_seconds=actual_tick_duration)

                print(f"--- Tick {current_tick} finished in {actual_tick_duration:.4f} seconds ---")

            print("\n--- Simulation Finished ---")

        except asyncio.CancelledError:
            print("Simulation task was cancelled.")
        except Exception as e:
            print(f"!!! Simulation loop failed with an error: {e}")
            import traceback

            traceback.print_exc()
            self._status = SimulationStatus.ERROR
            self._error_message = str(e)
        finally:
            print("Simulation loop finished. Triggering final cleanup.")
            await self.cleanup()
            self._status = SimulationStatus.STOPPED

    async def stop_simulation(self):
        """
        Stop the running simulation.

        Returns:
            dict: The current simulation status.
        """
        if self._status not in [SimulationStatus.RUNNING, SimulationStatus.STARTING]:
            print("Simulation is not running or starting, no need to stop.")
            await self.cleanup()
            self._status = SimulationStatus.STOPPED
            return self.status

        if self._status == SimulationStatus.STOPPING:
            print("Simulation is already stopping.")
            return self.status

        self._status = SimulationStatus.STOPPING
        print("Stopping simulation task...")

        if self._simulation_task and not self._simulation_task.done():
            self._simulation_task.cancel()
            try:
                await self._simulation_task
            except asyncio.CancelledError:
                pass

        await self.cleanup()
        self._status = SimulationStatus.STOPPED
        print("Simulation stopped.")
        return self.status

    async def cleanup(self):
        """
        Clean up simulation resources including Ray actors.
        """
        print("Cleaning up simulation resources...")

        if ray.is_initialized():
            try:
                pod_manager_actor = ray.get_actor("global_pod_manager")
                print("Found named actor 'global_pod_manager', killing it...")
                ray.kill(pod_manager_actor)
                self._pod_manager = None
            except ValueError:
                print("Named actor 'global_pod_manager' not found, might have been cleaned up already.")

        if self._system:
            try:
                await self._system.close()
            except Exception as e:
                print(f"Error closing system components: {e}")
            self._system = None

        if ray.is_initialized():
            print("Shutting down Ray...")
            ray.shutdown()

        self._builder = None
        self._simulation_task = None
        print("Cleanup complete.")

    async def execute_god_command(self, command: str, params: Dict[str, Any]):
        """
        Execute a god mode command on the PodManager.

        Args:
            command (str): The name of the command to execute.
            params (Dict[str, Any]): The parameters for the command.

        Returns:
            Any: The result of the command execution.

        Raises:
            Exception: If simulation is not running or command is invalid.
        """
        if self._status != SimulationStatus.RUNNING or not self._pod_manager:
            raise Exception("Simulation is not running.")

        if command == "deliver_message":
            message_dict = params.get("message")
            if isinstance(message_dict, dict):
                try:
                    msg_data = message_dict.copy()
                    if "created_at" in msg_data and isinstance(msg_data["created_at"], str):
                        try:
                            msg_data["created_at"] = datetime.fromisoformat(msg_data["created_at"])
                        except ValueError:
                            msg_data["created_at"] = datetime.now()
                    elif "created_at" not in msg_data:
                        msg_data["created_at"] = datetime.now()

                    message_obj = Message(**msg_data)
                    params["message"] = message_obj
                except Exception as e:
                    raise ValueError(f"Invalid 'message' payload for deliver_message command: {e}")
            else:
                raise ValueError("The 'deliver_message' command requires a 'message' object in its parameters.")

        if not hasattr(self._pod_manager, command):
            raise Exception(f"PodManager does not have a command named '{command}'")

        method = getattr(self._pod_manager, command)

        params.pop("_ray_trace_ctx", None)

        result = await method.remote(**params)

        if command == "close" and result is True:
            print("`close` command executed successfully. Stopping simulation loop.")
            asyncio.create_task(self.stop_simulation())

        return result


simulation_manager = SimulationManager()
