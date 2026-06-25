import boto3
import uuid
import os
from botocore.client import Config

s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
    config=Config(signature_version='s3v4')
)

def get_presigned_upload(file_name: str, file_type: str, upload_purpose: str, user_id: str) -> dict:
    bucket = os.getenv("S3_BUCKET_NAME")
    region = os.getenv("AWS_REGION")
    safe_name = file_name.replace(" ", "_")
    s3_key = f"{upload_purpose.lower()}s/{user_id}/{uuid.uuid4()}/{safe_name}"
    upload_url = s3.generate_presigned_url(
        'put_object',
        Params={'Bucket': bucket, 'Key': s3_key, 'ContentType': file_type},
        ExpiresIn=300
    )
    file_url = f"https://{bucket}.s3.{region}.amazonaws.com/{s3_key}"
    return {"upload_url": upload_url, "file_url": file_url, "expires_in": 300}

def get_presigned_download(file_url: str) -> dict:
    bucket = os.getenv("S3_BUCKET_NAME")
    s3_key = file_url.split(".amazonaws.com/")[-1]
    if not s3_key or s3_key == file_url:
        raise ValueError("Invalid S3 URL")
    download_url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': s3_key},
        ExpiresIn=300
    )
    return {"download_url": download_url, "expires_in": 300}
