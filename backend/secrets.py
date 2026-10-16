"""Reading secrets with the instance's IAM role. No long-lived keys, nothing written to disk."""
from __future__ import annotations

import json
from typing import Callable

SecretFetcher = Callable[[str, str], str]


def fetch_secret_from_aws(secret_arn: str, region: str) -> str:
    """Return one secret's string value. Needs only secretsmanager:GetSecretValue on that secret."""
    import boto3  # imported lazily: only needed on AWS, not for local SQLite development

    client = boto3.client("secretsmanager", region_name=region or None)
    return client.get_secret_value(SecretId=secret_arn)["SecretString"]


def read_json_secret(secret_arn: str, region: str, fetcher: SecretFetcher = fetch_secret_from_aws) -> dict:
    return json.loads(fetcher(secret_arn, region))
