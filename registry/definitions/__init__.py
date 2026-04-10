"""
lottery_engine/registry/definitions/__init__.py
Aggregates all state job definitions and source mappings.
To add a new state: create definitions/{state}.py and import here.
"""
from .georgia import JOB_DEFINITIONS as _GA_JOBS, SOURCE_MAPPINGS as _GA_MAPS
from .florida import JOB_DEFINITIONS as _FL_JOBS, SOURCE_MAPPINGS as _FL_MAPS

ALL_JOB_DEFINITIONS = _GA_JOBS + _FL_JOBS
ALL_SOURCE_MAPPINGS = _GA_MAPS + _FL_MAPS

__all__ = ["ALL_JOB_DEFINITIONS", "ALL_SOURCE_MAPPINGS"]
