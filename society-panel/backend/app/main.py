"""
FastAPI application entry point for SOCIETY-PANEL backend.
"""

import asyncio
import inspect
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from typing import Dict, Any, List
from .api import files, configs, registry, requirements
from fastapi.middleware.cors import CORSMiddleware
from .services.simulation_manager import simulation_manager, SimulationStatus
from .services.log_watcher import log_watcher


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.

    Args:
        app (FastAPI): The FastAPI application instance.

    Yields:
        None: Control is yielded to the application during its lifetime.
    """
    print("SOCIETY-PANEL Backend is starting up...")
    await log_watcher.start_watching()
    yield
    print("SOCIETY-PANEL Backend is shutting down...")
    await log_watcher.stop_watching()
    await simulation_manager.cleanup()


app = FastAPI(
    title="Multi-Agent Simulation Management App",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(configs.router, prefix="/api/configs", tags=["Configs"])
app.include_router(registry.router, prefix="/api/registry", tags=["Registry"])
app.include_router(requirements.router, prefix="/api/requirements", tags=["Requirements"])


@app.get("/")
def read_root():
    """
    Root endpoint that returns a welcome message.

    Returns:
        dict: A dictionary containing the welcome message.
    """
    return {"message": "Welcome to the SOCIETY-PANEL Backend!"}


@app.post("/api/simulation/start", tags=["Simulation"])
async def start_simulation_endpoint():
    """
    Start the simulation.

    Returns:
        dict: The current simulation status.
    """
    status = await simulation_manager.start_simulation()
    return status


@app.post("/api/simulation/stop", tags=["Simulation"])
async def stop_simulation_endpoint():
    """
    Stop the simulation.

    Returns:
        dict: The current simulation status.
    """
    status = await simulation_manager.stop_simulation()
    return status


@app.get("/api/simulation/status", tags=["Simulation"])
async def get_simulation_status():
    """
    Get the current simulation status.

    Returns:
        dict: The current simulation status including error information if any.
    """
    return simulation_manager.status


@app.get("/api/simulation/commands", tags=["Simulation"])
async def get_pod_manager_commands():
    """
    Dynamically retrieve all callable commands and their signatures from PodManager.

    Returns:
        list: A list of command dictionaries containing name, documentation, and parameters.

    Raises:
        HTTPException: If simulation has not been started and failed to pre-initialize builder.
        HTTPException: If PodManager class is not found.
    """
    if simulation_manager._status == SimulationStatus.STOPPED:
        if not simulation_manager._builder:
            try:
                await simulation_manager.start_simulation()
                await simulation_manager.stop_simulation()
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Simulation has not been started, and failed to pre-initialize builder to get commands: {e}"
                )
    if not simulation_manager._builder or not simulation_manager._builder._pod_manager_class:
        raise HTTPException(status_code=404, detail="PodManager class not found. Is the simulation configured?")

    pod_manager_class = simulation_manager._builder._pod_manager_class
    if hasattr(pod_manager_class, '__ray_metadata__'):
        original_class = pod_manager_class.__ray_metadata__.modified_class
    else:
        original_class = pod_manager_class

    commands = []
    for name, method in inspect.getmembers(original_class):
        if not name.startswith('_') and inspect.isfunction(method) and name not in ["init", "post_init"]:
            sig = inspect.signature(method)
            doc = inspect.getdoc(method) or "No description available."

            params_info = []
            for param in sig.parameters.values():
                if param.name == 'self':
                    continue

                param_type = str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any'
                param_type = param_type.replace("<class '", "").replace("'>", "")
                default_value = "required"
                if param.default != inspect.Parameter.empty:
                    default_value = param.default
                params_info.append({
                    "name": param.name,
                    "type": param_type,
                    "default": default_value
                })
            commands.append({
                "name": name,
                "doc": doc.strip(),
                "parameters": params_info
            })

    return sorted(commands, key=lambda x: x['name'])


@app.post("/api/simulation/command", tags=["Simulation"])
async def execute_command_endpoint(payload: Dict[str, Any]):
    """
    Execute a god mode command on the simulation.

    Args:
        payload (Dict[str, Any]): The command payload containing 'command' and 'params'.

    Returns:
        dict: The execution result with status and result data.

    Raises:
        HTTPException: If command is not specified in the payload.
    """
    command = payload.get("command")
    params = payload.get("params", {})
    if not command:
        raise HTTPException(status_code=400, detail="Command not specified.")

    result = await simulation_manager.execute_god_command(command, params)
    return {"status": "success", "result": result}


@app.websocket("/ws")
async def websocket_log_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time log streaming.

    Clients connect to receive formatted log entries as they are written.
    Log format:
    {
        "tick": "HH:MM:SS",
        "name": "[LEVEL] source",
        "payload": "module.func() → message",
        "category": "agent|environment|simulation|system|framework",
        "level": "DEBUG|INFO|WARNING|ERROR",
        "full_timestamp": "YYYY-MM-DD HH:MM:SS",
        "module": "module.name",
        "function": "function_name"
    }
    """
    await websocket.accept()
    
    log_queue = log_watcher.subscribe()
    
    try:
        await websocket.send_json({
            "tick": "SYS",
            "name": "SYSTEM",
            "payload": "Connected to log stream. Waiting for new log entries...",
            "category": "system",
            "level": "INFO"
        })
        
        while True:
            try:
                log_entry = await asyncio.wait_for(log_queue.get(), timeout=30.0)
                await websocket.send_json(log_entry)
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "tick": "SYS",
                    "name": "HEARTBEAT",
                    "payload": "Connection alive",
                    "category": "system",
                    "level": "DEBUG"
                })
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        log_watcher.unsubscribe(log_queue)
