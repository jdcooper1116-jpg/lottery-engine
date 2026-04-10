"""
lottery_engine/registry/definitions/__init__.py
Aggregates all Wave 1 state definitions.
To add a new state: create definitions/{state}.py and import here.
"""
from .georgia     import JOB_DEFINITIONS as _GA_J, SOURCE_MAPPINGS as _GA_M
from .florida     import JOB_DEFINITIONS as _FL_J, SOURCE_MAPPINGS as _FL_M
from .new_york    import JOB_DEFINITIONS as _NY_J, SOURCE_MAPPINGS as _NY_M
from .pennsylvania import JOB_DEFINITIONS as _PA_J, SOURCE_MAPPINGS as _PA_M
from .ohio        import JOB_DEFINITIONS as _OH_J, SOURCE_MAPPINGS as _OH_M
from .michigan    import JOB_DEFINITIONS as _MI_J, SOURCE_MAPPINGS as _MI_M
from .illinois    import JOB_DEFINITIONS as _IL_J, SOURCE_MAPPINGS as _IL_M
from .tennessee   import JOB_DEFINITIONS as _TN_J, SOURCE_MAPPINGS as _TN_M
from .california  import JOB_DEFINITIONS as _CA_J, SOURCE_MAPPINGS as _CA_M
from .texas       import JOB_DEFINITIONS as _TX_J, SOURCE_MAPPINGS as _TX_M
from .oregon      import JOB_DEFINITIONS as _OR_J, SOURCE_MAPPINGS as _OR_M

ALL_JOB_DEFINITIONS = (
    _GA_J + _FL_J + _NY_J + _PA_J + _OH_J + _MI_J +
    _IL_J + _TN_J + _CA_J + _TX_J + _OR_J
)
ALL_SOURCE_MAPPINGS = (
    _GA_M + _FL_M + _NY_M + _PA_M + _OH_M + _MI_M +
    _IL_M + _TN_M + _CA_M + _TX_M + _OR_M
)

__all__ = ["ALL_JOB_DEFINITIONS", "ALL_SOURCE_MAPPINGS"]
