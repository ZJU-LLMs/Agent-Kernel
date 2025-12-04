"python -m examples.standalone_test.run_simulation"

import sys
import os
import asyncio
import yaml
import time

project_path = os.path.dirname(os.path.abspath(__file__))

os.environ["MAS_PROJECT_ABS_PATH"] = project_path
if "MAS_PROJECT_REL_PATH" not in os.environ:
    os.environ["MAS_PROJECT_REL_PATH"] = "examples.standalone_test"

from agentkernel_standalone.mas.builder import Builder
from examples.standalone_test.registry import RESOURCES_MAPS
from agentkernel_standalone.toolkit.logger import get_logger

from examples.standalone_test.custom_controller import CustomController

logger = get_logger(__name__)


async def main():
    """Async main function to assemble and start the simulation"""
    controller = None
    system = None
    try:
        logger.info(f"Project path set to: {project_path}")

        logger.info("Creating simulation builder...")
        sim_builder = Builder(project_path=project_path, resource_maps=RESOURCES_MAPS)

        logger.info("Assembling all simulation components...")
        controller, system = await sim_builder.init()

        # --- Simulation Loop ---
        max_ticks = sim_builder.config.simulation.max_ticks
        logger.info(f"--- Starting Simulation Run for {max_ticks} ticks ---")

        num_ticks_to_run = max_ticks

        total_duration = 0
        for i in range(num_ticks_to_run):

            tick_start_time = time.time()

            await controller.step_agent()
            await system.run("messager", "dispatch_messages")

            if isinstance(controller, CustomController):
                await controller.update_agents_status()

            tick_end_time = time.time()
            actual_tick_duration = tick_end_time - tick_start_time
            total_duration += actual_tick_duration

            current_tick = await system.run("timer", "get_tick")
            await system.run("timer", "add_tick", duration_seconds=actual_tick_duration)

            logger.info(f"--- Tick {current_tick} finished in {actual_tick_duration:.4f} seconds ---")

        if num_ticks_to_run > 0:
            average_time_per_tick = total_duration / num_ticks_to_run
            logger.info(f"\n--- Ran {num_ticks_to_run} ticks. Average time per tick: {average_time_per_tick:.4f} seconds ---")

        logger.info("\n--- Simulation Finished ---")
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        logger.exception("An unhandled exception occurred during simulation.")
    finally:
        if controller:
            result = await controller.close()
            logger.info(f"Controller close result is {result}")
        if system:
            result = await system.close()
            logger.info(f"System close result is {result}")


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user. Exiting.")
    finally:
        logger.info("Simulation ended.")
