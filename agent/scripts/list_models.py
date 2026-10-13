#!/usr/bin/env python3
"""
Bedrock Model Listing Script.

Lists foundation models (filtered to text output) and inference profiles
for the configured AWS region.
Helps confirm exact model IDs (e.g. Qwen models) to place into agent/config.yaml.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path so agent module can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agent.llm import find_and_load_env, clean_env_vars, load_config, handle_llm_error

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    print("Error: boto3 is not installed. Please run `pip install boto3` or activate the virtual environment.")
    sys.exit(1)


def main() -> None:
    # 1. Load environment and configuration
    env_file = find_and_load_env()
    clean_env_vars()
    config = load_config()

    bedrock_cfg = config.get("bedrock", {})
    region = os.getenv("AWS_REGION", bedrock_cfg.get("region", "us-east-1"))
    bearer_token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    profile = os.getenv("AWS_PROFILE")

    print("=" * 70)
    print("Amazon Bedrock Model Listing")
    print(f"Env file: {env_file}")
    print(f"Region:   {region}")
    print(f"Auth:     {'Bearer Token / API Key' if bearer_token else ('Named Profile: ' + profile if profile else 'Standard AWS Keys / Role')}")
    print("=" * 70)

    # 2. Initialize boto3 bedrock client
    session_kwargs = {"region_name": region}
    if profile:
        session = boto3.Session(profile_name=profile, **session_kwargs)
        client = session.client("bedrock")
    else:
        client = boto3.client("bedrock", **session_kwargs)

    # 3. List Foundation Models (filtered to text output)
    print("\n--- Foundation Models (Text Output) ---")
    try:
        response = client.list_foundation_models(byOutputModality="TEXT")
        models = response.get("modelSummaries", [])

        if not models:
            print("No text models found.")
        else:
            print(f"Found {len(models)} text foundation model(s):\n")
            print(f"{'Provider':<18} | {'Model Name':<35} | {'Model ID'}")
            print("-" * 85)

            qwen_models = []
            for m in models:
                provider = m.get("providerName", "Unknown")
                name = m.get("modelName", "Unknown")
                model_id = m.get("modelId", "Unknown")
                
                # Check for Qwen
                if "qwen" in provider.lower() or "qwen" in model_id.lower() or "qwen" in name.lower():
                    qwen_models.append((provider, name, model_id))

                print(f"{provider:<18} | {name:<35} | {model_id}")

            if qwen_models:
                print("\n" + "=" * 70)
                print(">>> Qwen Models Found:")
                for p, n, mid in qwen_models:
                    print(f"  * Provider: {p} | Name: {n} | ID: {mid}")
                print("=" * 70)

    except Exception as e:
        print("\nCould not list foundation models:")
        print(handle_llm_error(e))

    # 4. List Inference Profiles (if allowed by the Bedrock API)
    print("\n--- Cross-Region / Inference Profiles ---")
    try:
        if hasattr(client, "list_inference_profiles"):
            profiles_resp = client.list_inference_profiles()
            profiles = profiles_resp.get("inferenceProfileSummaries", [])
            if not profiles:
                print("No inference profiles found.")
            else:
                print(f"Found {len(profiles)} inference profile(s):\n")
                print(f"{'Profile Name':<40} | {'Profile ID'}")
                print("-" * 80)
                for p in profiles:
                    p_name = p.get("inferenceProfileName", "Unknown")
                    p_id = p.get("inferenceProfileId", "Unknown")
                    print(f"{p_name:<40} | {p_id}")
        else:
            print("Inference profile listing is not supported by this boto3 version.")
    except Exception as e:
        print("Could not list inference profiles:")
        print(handle_llm_error(e))

    print("\n" + "=" * 70)
    print("Done. Copy the desired model ID into agent/config.yaml under bedrock.model_id.")
    print("=" * 70)


if __name__ == "__main__":
    main()
