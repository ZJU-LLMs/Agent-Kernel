"""Module for sampling attribute values based on configurations."""

import random
import numpy as np
from typing import Dict, Any


def sample(
    attr_config: Dict[str, Any],
    generated_attrs: Dict[str, Any] = {},
    py_rng: random.Random = None,
    np_rng: np.random.default_rng = None,
) -> Any:
    """
    Sample a value based on the provided attribute configuration.

    This function supports various sampling types, including absolute values,
    categorical choices, ranges, distributions, and conditional sampling.

    Args:
        attr_config (Dict[str, Any]): The configuration for the attribute.
        generated_attrs (Dict[str, Any]): A dictionary of already generated attributes.
        py_rng (Optional[random.Random]): A Python random number generator instance.
        np_rng (Optional[np.random.default_rng]): A NumPy random number generator instance.

    Returns:
        Any: The sampled value.

    Raises:
        ValueError: If an unknown attribute type is provided or a dependency is missing.
    """
    type = attr_config["type"]

    if type == "absolute":
        return attr_config["value"]

    elif type == "categorical":
        choices, weights = zip(*[(c["value"], c["weight"]) for c in attr_config["choices"]])
        return py_rng.choices(choices, weights=weights, k=1)[0]

    elif type == "range":
        return py_rng.randint(attr_config["min"], attr_config["max"])

    elif type == "uniform":
        return round(py_rng.uniform(attr_config["min"], attr_config["max"]), 2)

    elif type == "normal":
        val = np_rng.normal(attr_config["mean"], attr_config["std"])
        val = np.clip(val, attr_config["min"], attr_config["max"])
        return round(float(val), 2)

    elif type == "draw_k":
        k_choices, k_weights = zip(*[(c["value"], c["weight"]) for c in attr_config["k"]["choices"]])
        k = py_rng.choices(k_choices, weights=k_weights, k=1)[0]

        vals, ws = zip(*[(c["value"], c["weight"]) for c in attr_config["choices"]])
        probs = np.array(ws) / sum(ws)

        return list(np_rng.choice(vals, size=min(k, len(vals)), replace=False, p=probs))

    elif type == "conditional":
        based_on = attr_config["based_on"]
        base_keys = [based_on] if isinstance(based_on, str) else list(based_on)

        for k in base_keys:
            if k not in generated_attrs:
                raise ValueError(f"Conditional attribute depends on {k}, which is missing.")

        for condition in attr_config.get("conditions", []):
            cond_map = condition.get("when")
            if not cond_map:
                continue

            match = True
            for key, allowed in cond_map.items():
                if key not in generated_attrs:
                    match = False
                    break
                if isinstance(allowed, (str, int, float)):
                    allowed = [allowed]
                if generated_attrs[key] not in allowed:
                    match = False
                    break

            if match:
                choices, weights = zip(*[(c["value"], c["weight"]) for c in condition["choices"]])
                return py_rng.choices(choices, weights=weights, k=1)[0]

        return attr_config.get("default", None)

    else:
        raise ValueError(f"Unknown attribute type: {type}")
