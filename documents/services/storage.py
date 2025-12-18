import os
from pathlib import Path
from typing import Tuple

import boto3
from django.conf import settings


def _store_local(doc, pdf_bytes: bytes) -> Tuple[str, str]:
    base_path: Path = Path(settings.DOCUMENT_STORAGE_PATH)
    base_path.mkdir(parents=True, exist_ok=True)
    filename = f"{doc.id}_{doc.doc_type}_{doc.term}.pdf"
    dest = base_path / filename
    dest.write_bytes(pdf_bytes)
    url = os.path.join(settings.DOCUMENT_BASE_URL, filename)
    return url, str(dest)


def _store_s3(doc, pdf_bytes: bytes) -> Tuple[str, str]:
    session = boto3.session.Session(
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=getattr(settings, "AWS_REGION", None),
    )
    client = session.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        config=boto3.session.Config(s3={"addressing_style": "virtual"}),
    )
    filename = f"{doc.id}_{doc.doc_type}_{doc.term}.pdf"
    client.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=filename, Body=pdf_bytes, ContentType="application/pdf")
    base_url = getattr(settings, "DOCUMENT_BASE_URL", None)
    if base_url:
        url = f"{base_url.rstrip('/')}/{filename}"
    else:
        # fallback compatible avec virtual-hosted style
        endpoint = (settings.AWS_S3_ENDPOINT_URL or "").rstrip("/")
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        url = f"{endpoint}/{bucket}/{filename}"
    return url, filename


def store_pdf(doc, pdf_bytes: bytes) -> Tuple[str, str]:
    if getattr(settings, "DOCUMENT_STORAGE", "local") == "s3":
        return _store_s3(doc, pdf_bytes)
    return _store_local(doc, pdf_bytes)
