"""Start mit ``python -m app`` (ohne Docker, z. B. auf dem Raspberry Pi)."""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("SOLARPILOT_HOST", "0.0.0.0"),  # noqa: S104
        port=int(os.environ.get("SOLARPILOT_PORT", "8000")),
        proxy_headers=True,
    )
