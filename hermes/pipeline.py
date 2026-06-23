"""Compatibility shim for the renamed workflow module.

New code should import from ``hermes.workflow``.
"""

from hermes.workflow import (
    DEFAULT_OUTPUTS,
    DEFAULT_PROPERTIES,
    run_config,
    run_pipeline_config,
    run_volume,
    run_volume_pipeline,
    run_workspace,
    run_workspace_pipeline,
)

__all__ = [
    "DEFAULT_OUTPUTS",
    "DEFAULT_PROPERTIES",
    "run_config",
    "run_pipeline_config",
    "run_volume",
    "run_volume_pipeline",
    "run_workspace",
    "run_workspace_pipeline",
]
