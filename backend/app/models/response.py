from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AnalysisResponse(BaseModel):
    """
    Standard response returned by CyberShield after URL analysis.
    """

    success: bool = Field(
        ...,
        description="Whether the analysis completed successfully."
    )

    url: str = Field(
        ...,
        description="Original URL submitted by the user."
    )

    normalized_url: Optional[str] = Field(
        default=None,
        description="Normalized URL used internally."
    )

    exists: bool = Field(
        ...,
        description="Whether the website is reachable."
    )

    phishing_probability: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
        description="Predicted phishing probability (0-100%)."
    )

    risk: str = Field(
        default="Unknown",
        description="Overall risk level."
    )

    message: str = Field(
        default="Analysis completed successfully.",
        description="General response message."
    )

    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Combined output from all analyzers."
    )


class TextAnalysisResponse(BaseModel):
    success: bool
    text: str
    phishing_probability: Optional[float] = Field(default=None, ge=0, le=100)
    risk: str = "Unknown"
    message: str = "Analysis completed successfully."
    data: Dict[str, Any] = Field(default_factory=dict)
