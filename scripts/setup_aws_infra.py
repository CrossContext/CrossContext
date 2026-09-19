"""
OmniContext - Automated Amazon OpenSearch Serverless (AOSS) Provisioning Script
Automatically creates:
1. Encryption Policy (KMS)
2. Network Policy (Public/VPC access for collection)
3. Data Access Policy (Grants current IAM caller full collection & index permissions)
4. Vector Search Collection ('omnicontext-code-index')
Usage:
    python scripts/setup_aws_infra.py
"""

import os
import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

import boto3


def setup_aoss():
    print("==================================================")
    print("  Provisioning Amazon OpenSearch Serverless (AOSS)")
    print("==================================================")

    region = os.getenv("AWS_REGION", "us-east-1")
    collection_name = "omnicontext-code-index"
    
    sts = boto3.client("sts", region_name=region)
    caller = sts.get_caller_identity()
    user_arn = caller["Arn"]
    print(f"Target Region:    {region}")
    print(f"Current IAM User: {user_arn}")
    print(f"Collection Name:  {collection_name}\n")

    aoss = boto3.client("opensearchserverless", region_name=region)

    # 1. Encryption Policy
    enc_policy_name = f"{collection_name}-enc"
    print(f"[1/4] Creating Encryption Security Policy '{enc_policy_name}'... ", end="")
    try:
        policy_doc = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{collection_name}"]
                }
            ],
            "AWSOwnedKey": True
        }
        aoss.create_security_policy(
            name=enc_policy_name,
            type="encryption",
            policy=json.dumps(policy_doc)
        )
        print("OK")
    except aoss.exceptions.ConflictException:
        print("ALREADY EXISTS")
    except Exception as e:
        print(f"ERROR: {e}")

    # 2. Network Policy
    net_policy_name = f"{collection_name}-net"
    print(f"[2/4] Creating Network Security Policy '{net_policy_name}'... ", end="")
    try:
        net_doc = [
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"]
                    },
                    {
                        "ResourceType": "dashboard",
                        "Resource": [f"collection/{collection_name}"]
                    }
                ],
                "AllowFromPublic": True
            }
        ]
        aoss.create_security_policy(
            name=net_policy_name,
            type="network",
            policy=json.dumps(net_doc)
        )
        print("OK")
    except aoss.exceptions.ConflictException:
        print("ALREADY EXISTS")
    except Exception as e:
        print(f"ERROR: {e}")

    # 3. Data Access Policy
    access_policy_name = f"{collection_name}-access"
    print(f"[3/4] Creating Data Access Policy '{access_policy_name}'... ", end="")
    try:
        data_doc = [
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{collection_name}"],
                        "Permission": [
                            "aoss:CreateCollectionItems",
                            "aoss:DeleteCollectionItems",
                            "aoss:UpdateCollectionItems",
                            "aoss:DescribeCollectionItems"
                        ]
                    },
                    {
                        "ResourceType": "index",
                        "Resource": [f"index/{collection_name}/*"],
                        "Permission": [
                            "aoss:CreateIndex",
                            "aoss:DeleteIndex",
                            "aoss:UpdateIndex",
                            "aoss:DescribeIndex",
                            "aoss:ReadDocument",
                            "aoss:WriteDocument"
                        ]
                    }
                ],
                "Principal": [user_arn]
            }
        ]
        aoss.create_access_policy(
            name=access_policy_name,
            type="data",
            policy=json.dumps(data_doc)
        )
        print("OK")
    except aoss.exceptions.ConflictException:
        print("ALREADY EXISTS")
    except Exception as e:
        print(f"ERROR: {e}")

    # 4. Create Collection
    print(f"[4/4] Creating Vector Search Collection '{collection_name}'... ", end="")
    try:
        res = aoss.create_collection(
            name=collection_name,
            type="VECTORSEARCH",
            description="Vector search collection for OmniContext AST semantic chunks"
        )
        print("CREATING (takes ~1-2 minutes)")
    except aoss.exceptions.ConflictException:
        print("ALREADY EXISTS")
    except Exception as e:
        print(f"ERROR: {e}")

    # Wait for collection to be ACTIVE and retrieve endpoint
    print("\nPolling for collection to become ACTIVE...")
    endpoint = ""
    for _ in range(30):
        try:
            desc = aoss.batch_get_collection(names=[collection_name])
            details = desc.get("collectionDetails", [])
            if details:
                status = details[0].get("status")
                endpoint = details[0].get("collectionEndpoint", "")
                if status == "ACTIVE" and endpoint:
                    print(f"Collection is ACTIVE!")
                    break
                else:
                    print(f"Status: {status} ... waiting 10s")
            time.sleep(10)
        except Exception:
            time.sleep(10)

    print("\n" + "=" * 50)
    print("PROVISIONING COMPLETED!")
    print("=" * 50)
    if endpoint:
        print(f"Your Collection Endpoint: {endpoint}")
        print(f"\nUpdate your .env file with:")
        print(f"AOSS_ENDPOINT={endpoint}")
        print(f"AOSS_INDEX_NAME={collection_name}")
    else:
        print("Collection creation initiated. Once ACTIVE, check AWS Console for the collection endpoint URL.")


if __name__ == "__main__":
    setup_aoss()
