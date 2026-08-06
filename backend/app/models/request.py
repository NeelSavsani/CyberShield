from pydantic import BaseModel, Field, field_validator


class URLRequest(BaseModel):
    """
    Request model for URL analysis.
    """

    url: str = Field(
        ...,
        min_length=4,
        max_length=2048,
        description="Website URL to analyze",
        examples=["https://example.com"]
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """
        Basic validation before deeper URL normalization.
        """

        value = value.strip()

        if not value:
            raise ValueError("URL cannot be empty.")

        if " " in value:
            raise ValueError("URL cannot contain spaces.")

        if value.lower().startswith(("javascript:", "data:", "file:")):
            raise ValueError("Unsupported URL scheme.")

        return value