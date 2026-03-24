from .company import (
    StartupProfile,
    DimensionScore,
    StartupScreeningResult,
    ValuationMetrics,
    PublicCompanyProfile,
    CatalystEvent,
    # Backward-compatible aliases
    PrivateCompany,
    PublicCompany,
    Catalyst,
)
from .report import (
    TeamProfile,
    TechnologyProfile,
    MoatProfile,
    PipelineProfile,
    BusinessModelProfile,
    EvidenceItem,
    InferenceItem,
    CompanyDiligenceMemo,
    ValidationIssue,
    ValidationReport,
    FinalReport,
    # Backward-compatible alias
    DiligenceResult,
)

__all__ = [
    # Current names
    "StartupProfile",
    "DimensionScore",
    "StartupScreeningResult",
    "ValuationMetrics",
    "PublicCompanyProfile",
    "CatalystEvent",
    "TeamProfile",
    "TechnologyProfile",
    "MoatProfile",
    "PipelineProfile",
    "BusinessModelProfile",
    "EvidenceItem",
    "InferenceItem",
    "CompanyDiligenceMemo",
    "ValidationIssue",
    "ValidationReport",
    "FinalReport",
    # Backward-compatible aliases
    "PrivateCompany",
    "PublicCompany",
    "Catalyst",
    "DiligenceResult",
]
