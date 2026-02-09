import os

# Keep unit tests deterministic and lightweight even if local .env is set to AGENT_MODE=hybrid.
os.environ["AGENT_MODE"] = "deterministic"
