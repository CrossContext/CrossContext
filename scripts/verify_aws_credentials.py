"""
CrossContext - AWS Credentials & Bedrock Model Access Verification Script
Run this script after configuring your AWS credentials in .env to verify:
1. AWS IAM Credentials validity (STS GetCallerIdentity)
2. Amazon Bedrock Runtime access for Anthropic Claude 3.5 / 3.7 Sonnet
3. Amazon Bedrock Titan Text Embeddings v2 access
4. Amazon OpenSearch Serverless (AOSS) access
Usage:
    python scripts/verify_aws_credentials.py
"""

import os
import sys
import json
from pathlib import Path

# Setup sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass


def verify_aws():
    print("==================================================")
    print("   CrossContext AWS Cloud Readiness Verification   ")
    print("==================================================")

    region = os.getenv("AWS_REGION", "us-east-1")
    print(f"Target AWS Region: {region}\n")

    # 1. Verify boto3 installation
    try:
        import boto3
        import botocore.exceptions
    except ImportError:
        print("[FAIL] 'boto3' is not installed. Please run: pip install boto3")
        sys.exit(1)

    # 2. Check STS Identity (Credentials Validity)
    print("[1/4] Checking AWS IAM Credentials (STS)... ", end="")
    try:
        sts = boto3.client("sts", region_name=region)
        identity = sts.get_caller_identity()
        print("OK")
        print(f"      Account ID: {identity.get('Account')}")
        print(f"      IAM ARN:    {identity.get('Arn')}")
    except Exception as e:
        print(f"FAIL\n      Error: {e}")
        print("\n[Action Required]: Please configure your AWS credentials.")
        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your .env file or run 'aws configure'.")
        sys.exit(1)

    # 3. Check Amazon Bedrock Runtime (Titan Text Embeddings v2)
    embedding_model = os.getenv("BEDROCK_EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
    print(f"\n[2/4] Testing Bedrock Embedding Model ({embedding_model})... ", end="")
    try:
        bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)
        payload = {
            "inputText": "CrossContext cross-repository code retrieval test.",
            "dimensions": 1024,
            "normalize": True
        }
        res = bedrock_runtime.invoke_model(
            modelId=embedding_model,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload)
        )
        body = json.loads(res["body"].read())
        vec = body.get("embedding", [])
        print(f"OK (Generated {len(vec)}-dimensional vector)")
    except Exception as e:
        print(f"FAIL\n      Error: {e}")
        print("\n[Action Required]: Bedrock Model Access not enabled.")
        print(f"Go to AWS Console -> Amazon Bedrock (Region: {region}) -> 'Model Access' (left sidebar).")
        print(f"Request access for '{embedding_model}'. (Approval is usually instant).")

    # 4. Check Amazon Bedrock Claude Sonnet Access
    env_claude_model = os.getenv("BEDROCK_MODEL_ID", "")
    candidate_models = []
    if env_claude_model:
        candidate_models.append(env_claude_model)
    # Common Sonnet 4.5 and Sonnet 4 model identifiers (direct and cross-region inference profiles)
    candidate_models.extend([
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "anthropic.claude-sonnet-4-5-20250929-v1:0",
        "us.anthropic.claude-sonnet-4-20250514-v1:0",
        "anthropic.claude-sonnet-4-20250514-v1:0",
        "anthropic.claude-3-5-sonnet-20241022-v2:0",
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    ])

    print(f"\n[3/4] Testing Bedrock Claude Sonnet...")
    claude_success = False
    working_model = None

    for model_id in candidate_models:
        print(f"      Trying '{model_id}'... ", end="")
        try:
            claude_payload = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 50,
                "messages": [
                    {"role": "user", "content": "Respond with the single word: READY"}
                ]
            }
            res = bedrock_runtime.invoke_model(
                modelId=model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(claude_payload)
            )
            body = json.loads(res["body"].read())
            reply = body.get("content", [{}])[0].get("text", "").strip()
            print(f"SUCCESS! (Response: '{reply}')")
            claude_success = True
            working_model = model_id
            break
        except Exception as e:
            err_msg = str(e)
            if "AccessDeniedException" in err_msg:
                print("AccessDenied")
            elif "ResourceNotFoundException" in err_msg or "ValidationException" in err_msg:
                print("Not available with this ID")
            else:
                print(f"Error: {e}")

    if claude_success and working_model:
        print(f"      --> ACTIVE SONNET MODEL: {working_model}")
        print(f"      Make sure your .env has: BEDROCK_MODEL_ID={working_model}")
    else:
        print("\n[Action Required]: Click on 'Claude Sonnet 4.5' in the Bedrock console to view its exact Model ID / Inference Profile ID.")

    # 5. Check OpenSearch Serverless (AOSS)
    aoss_endpoint = os.getenv("AOSS_ENDPOINT", "")
    print(f"\n[4/4] Checking Amazon OpenSearch Serverless (AOSS)... ", end="")
    if not aoss_endpoint:
        print("NOT CONFIGURED YET (Optional)")
        print("      To provision AOSS, run: python scripts/setup_aws_infra.py")
    else:
        try:
            aoss = boto3.client("opensearchserverless", region_name=region)
            collections = aoss.list_collections().get("collectionSummaries", [])
            print(f"OK (Found {len(collections)} collection(s))")
        except Exception as e:
            print(f"WARNING ({e})")

    print("\n==================================================")
    print("Verification complete! Check details above.")
    print("==================================================")


if __name__ == "__main__":
    verify_aws()
