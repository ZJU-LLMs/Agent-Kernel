# Introduction
This example demonstrates how to build a simple Multi-Agent System using Agent-Kernel, designed to help users understand the execution flow and facilitate future extensions.

To simplify the process, we have provided basic implementations for five core plugins: Perceive, Plan, Invoke, Communication, and Space. The remaining plugins are structured as placeholders (using pass) to allow for easy customization and expansion by the user.

# Quick Start
1. Prepare the dataset:
   
    I. **Make directories**:
    ```
    Agent-Kernel
    ├──data/
        ├── agents/
        │   └── profiles.jsonl
        ├── map/
        │   └── agents.jsonl
        └── relation/
            └── relation.jsonl
    ```
    II. **Make some sample data**:
    ```
        **profiles.jsonl**
            {"id": "Alice", "name": "Alice"}
            {"id": "Bob", "name": "Bob"}
            ...

        **agents.jsonl**
            {"id": "Alice", "position": [0, 0]}
            {"id": "Bob", "position": [10, 10]}
            ...

        **relation.jsonl**

            [empty]
    ```
2. Set your api key
    ```yaml
        **Agent-Kernel/standalone_test/configs/models_config.yaml**
        - name: OpenAIProvider
        model: your-model-name
        api_key: your-api-key
        base_url: your-base-url
        capabilities: ["your-capabilities"] # e.g., capabilities: ["chat"]
    ```
    
3. Install the required dependencies:
    ```bash
    pip install agentkernel-standalone
    ```
    
4. Run
    ```bash
    cd Agent-Kernel
    python -m examples.standalone_test.run_simulation
    ```

        
            
