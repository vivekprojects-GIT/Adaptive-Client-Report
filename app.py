"""Entry point for the "Gradio SDK" Space.

There is no Gradio UI here. An HF Space with sdk: gradio is, underneath,
just a container that runs `python app.py` and proxies whatever binds to
$PORT — nothing requires that process to call gradio's own server. This
runs the real FastAPI app instead, which is how a full backend + React
frontend deploys on the free tier without a Docker-capable plan.

Locally this file is never used — `uvicorn ape.api:app --reload` is the
dev entry point, per the README. This one exists for the Space only.
"""

import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("ape.api:app", host="0.0.0.0",
               port=int(os.getenv("PORT", "7860")))
