"""Deploy FinDoc AI to HF Spaces (Streamlit SDK, free tier).

Reads HF_WRITE_TOKEN from env, GROQ_API_KEY from .env.
Uploads the project + the built vector store (data/processed/chroma_db)
and sets GROQ_API_KEY as a Space secret.
"""
import os
import sys
import time

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "src")

from dotenv import load_dotenv, dotenv_values
from huggingface_hub import HfApi


def main() -> None:
    token = os.environ.get("HF_WRITE_TOKEN", "").strip()
    if not token:
        sys.exit("ERROR: set HF_WRITE_TOKEN env var first.")

    load_dotenv(".env")
    groq_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not groq_key:
        sys.exit("ERROR: GROQ_API_KEY not found in .env")

    api = HfApi(token=token)
    user = api.whoami()["name"]
    repo_id = f"{user}/findoc-ai"
    print(f"Authenticated as: {user}")

    print(f"Ensuring space exists: {repo_id}")
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="streamlit",
            private=False,
            exist_ok=True,
        )
        print("  space ensured")
    except Exception as e:
        print("  create_repo note:", e)

    print("Uploading project (incl. vector store, excl. secrets/raw data)...")
    api.upload_folder(
        repo_id=repo_id,
        folder_path=".",
        repo_type="space",
        ignore_patterns=[
            ".git/*",
            ".env*",
            "logs/*",
            "data/raw/*",
            "data/eval/*",
            "__pycache__/*",
            "*.py[cod]",
            ".pytest_cache/*",
            "*.egg-info/*",
        ],
    )
    print("  upload done")

    print("Setting GROQ_API_KEY secret...")
    api.add_space_secret(repo_id=repo_id, key="GROQ_API_KEY", value=groq_key)
    print("  secret set")

    print(f"\nSpace URL: https://huggingface.co/spaces/{repo_id}")


if __name__ == "__main__":
    main()