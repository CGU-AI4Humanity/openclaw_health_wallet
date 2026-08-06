import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP


RETINA_URL = os.getenv(
    "RETINA_URL",
    "http://retina-tool:8000/predict",
)

RETINA_HEALTH_URL = os.getenv(
    "RETINA_HEALTH_URL",
    "http://retina-tool:8000/health",
)

mcp = FastMCP(
    name="Retina MCP",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    port=8000,
)


@mcp.tool()
async def analyze_retina_image(image_path: str) -> dict[str, Any]:
    """
    Analyze a retinal image using the Retina Tool.

    Args:
        image_path: Image path inside the MCP container,
                    such as /shared-images/test.jpg.
    """

    image = Path(image_path).resolve()

    if not image.exists():
        return {
            "status": "error",
            "message": f"Image not found: {image_path}",
        }

    if not image.is_file():
        return {
            "status": "error",
            "message": f"Path is not a file: {image_path}",
        }

    content_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    content_type = content_types.get(image.suffix.lower())

    if content_type is None:
        return {
            "status": "error",
            "message": "Only JPG, JPEG, and PNG images are supported.",
        }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with image.open("rb") as image_file:
                files = {
                    "image": (
                        image.name,
                        image_file,
                        content_type,
                    )
                }

                response = await client.post(
                    RETINA_URL,
                    files=files,
                )

        response.raise_for_status()

        return {
            "status": "success",
            "prediction": response.json(),
        }

    except httpx.ConnectError:
        return {
            "status": "error",
            "message": "Could not connect to the Retina Tool.",
        }

    except httpx.TimeoutException:
        return {
            "status": "error",
            "message": "Retina Tool request timed out.",
        }

    except httpx.HTTPStatusError as exc:
        return {
            "status": "error",
            "message": (
                f"Retina Tool returned HTTP "
                f"{exc.response.status_code}: "
                f"{exc.response.text}"
            ),
        }

    except ValueError:
        return {
            "status": "error",
            "message": "Retina Tool returned invalid JSON.",
        }


@mcp.tool()
async def health() -> dict[str, Any]:
    """Check connectivity between MCP and the Retina Tool."""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(RETINA_HEALTH_URL)

        response.raise_for_status()

        return {
            "status": "success",
            "retina_tool": response.json(),
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
        }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
