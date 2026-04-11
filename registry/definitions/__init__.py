"""
lottery_engine/registry/definitions/__init__.py
Aggregates all Wave 1 state definitions.
To add a new state: create definitions/{state}.py and import here.
"""
from .georgia        import JOB_DEFINITIONS as _GA_J, SOURCE_MAPPINGS as _GA_M
from .florida        import JOB_DEFINITIONS as _FL_J, SOURCE_MAPPINGS as _FL_M
from .new_york       import JOB_DEFINITIONS as _NY_J, SOURCE_MAPPINGS as _NY_M
from .pennsylvania   import JOB_DEFINITIONS as _PA_J, SOURCE_MAPPINGS as _PA_M
from .ohio           import JOB_DEFINITIONS as _OH_J, SOURCE_MAPPINGS as _OH_M
from .michigan       import JOB_DEFINITIONS as _MI_J, SOURCE_MAPPINGS as _MI_M
from .illinois       import JOB_DEFINITIONS as _IL_J, SOURCE_MAPPINGS as _IL_M
from .tennessee      import JOB_DEFINITIONS as _TN_J, SOURCE_MAPPINGS as _TN_M
from .california     import JOB_DEFINITIONS as _CA_J, SOURCE_MAPPINGS as _CA_M
from .texas          import JOB_DEFINITIONS as _TX_J, SOURCE_MAPPINGS as _TX_M
from .oregon         import JOB_DEFINITIONS as _OR_J, SOURCE_MAPPINGS as _OR_M
# Wave 2 — Batch 1
from .connecticut    import JOB_DEFINITIONS as _CT_J, SOURCE_MAPPINGS as _CT_M
from .delaware       import JOB_DEFINITIONS as _DE_J, SOURCE_MAPPINGS as _DE_M
from .indiana        import JOB_DEFINITIONS as _IN_J, SOURCE_MAPPINGS as _IN_M
from .maryland       import JOB_DEFINITIONS as _MD_J, SOURCE_MAPPINGS as _MD_M
from .south_carolina import JOB_DEFINITIONS as _SC_J, SOURCE_MAPPINGS as _SC_M
from .wisconsin      import JOB_DEFINITIONS as _WI_J, SOURCE_MAPPINGS as _WI_M
# Wave 2 — Batch 1
# Wave 2 — Sub-batch A
from .iowa           import JOB_DEFINITIONS as _IA_J, SOURCE_MAPPINGS as _IA_M
from .kansas         import JOB_DEFINITIONS as _KS_J, SOURCE_MAPPINGS as _KS_M
from .kentucky       import JOB_DEFINITIONS as _KY_J, SOURCE_MAPPINGS as _KY_M
from .nebraska       import JOB_DEFINITIONS as _NE_J, SOURCE_MAPPINGS as _NE_M
from .rhode_island   import JOB_DEFINITIONS as _RI_J, SOURCE_MAPPINGS as _RI_M
from .west_virginia  import JOB_DEFINITIONS as _WV_J, SOURCE_MAPPINGS as _WV_M

ALL_JOB_DEFINITIONS = (
    _GA_J + _FL_J + _NY_J + _PA_J + _OH_J + _MI_J +
    _IL_J + _TN_J + _CA_J + _TX_J + _OR_J +
    _CT_J + _DE_J + _IN_J + _MD_J + _SC_J + _WI_J +
    _IA_J + _KS_J + _KY_J + _NE_J + _RI_J + _WV_J
)
ALL_SOURCE_MAPPINGS = (
    _GA_M + _FL_M + _NY_M + _PA_M + _OH_M + _MI_M +
    _IL_M + _TN_M + _CA_M + _TX_M + _OR_M +
    _CT_M + _DE_M + _IN_M + _MD_M + _SC_M + _WI_M +
    _IA_M + _KS_M + _KY_M + _NE_M + _RI_M + _WV_M
)

__all__ = ["ALL_JOB_DEFINITIONS", "ALL_SOURCE_MAPPINGS"]
