import os
import tempfile
import urllib.parse
from typing import Optional
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

# Initialize S3 client
def get_s3_client():
    """Get configured S3 client."""
    return boto3.client(
        's3',
        endpoint_url=os.getenv('S3_ENDPOINT_URL'),
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    )

def parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    """
    Parse S3 URI into bucket and key.
    
    Args:
        s3_uri: S3 URI like s3://bucket/path/to/file
        
    Returns:
        Tuple of (bucket, key)
    """
    parsed = urllib.parse.urlparse(s3_uri)
    if parsed.scheme != 's3':
        raise ValueError(f"Invalid S3 URI: {s3_uri}")
    
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    
    return bucket, key

def download_to_tmp(s3_uri: str) -> str:
    """
    Download S3 object to temporary file.
    
    Args:
        s3_uri: S3 URI to download
        
    Returns:
        Path to temporary file
    """
    bucket, key = parse_s3_uri(s3_uri)
    
    # Create temporary file
    tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(key)[1])
    tmp_path = tmp_file.name
    tmp_file.close()
    
    try:
        s3_client = get_s3_client()
        s3_client.download_file(bucket, key, tmp_path)
        return tmp_path
    except (NoCredentialsError, ClientError) as e:
        os.unlink(tmp_path)  # Clean up temp file
        raise RuntimeError(f"Failed to download {s3_uri}: {e}")

def upload_bytes(bucket: str, key: str, content: bytes, 
                content_type: str = 'application/octet-stream') -> str:
    """
    Upload bytes to S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        content: Bytes to upload
        content_type: MIME content type
        
    Returns:
        S3 URI of uploaded object
    """
    try:
        s3_client = get_s3_client()
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type
        )
        return f"s3://{bucket}/{key}"
    except (NoCredentialsError, ClientError) as e:
        raise RuntimeError(f"Failed to upload to s3://{bucket}/{key}: {e}")

def get_presigned_url(bucket: str, key: str, expiration: int = 3600) -> str:
    """
    Generate presigned URL for S3 object.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiration: URL expiration in seconds
        
    Returns:
        Presigned URL
    """
    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
        return url
    except (NoCredentialsError, ClientError) as e:
        raise RuntimeError(f"Failed to generate presigned URL for s3://{bucket}/{key}: {e}")

def upload_file(file_path: str, bucket: str, key: str, 
               content_type: Optional[str] = None) -> str:
    """
    Upload local file to S3.
    
    Args:
        file_path: Local file path
        bucket: S3 bucket name
        key: S3 object key
        content_type: Optional MIME content type
        
    Returns:
        S3 URI of uploaded object
    """
    try:
        s3_client = get_s3_client()
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
            
        s3_client.upload_file(file_path, bucket, key, ExtraArgs=extra_args)
        return f"s3://{bucket}/{key}"
    except (NoCredentialsError, ClientError) as e:
        raise RuntimeError(f"Failed to upload {file_path} to s3://{bucket}/{key}: {e}")

def object_exists(bucket: str, key: str) -> bool:
    """
    Check if S3 object exists.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        True if object exists
    """
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise RuntimeError(f"Failed to check existence of s3://{bucket}/{key}: {e}")
    except NoCredentialsError as e:
        raise RuntimeError(f"No credentials available: {e}")