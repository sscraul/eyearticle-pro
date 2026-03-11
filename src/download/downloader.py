import httpx
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from loguru import logger
from fake_useragent import UserAgent

ua = UserAgent()

class DownloadError(Exception):
    pass

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError, DownloadError)),
    reraise=True
)
def download_pdf(url: str, save_path: str) -> bool:
    """
    Downloads a PDF from the given URL and saves it to save_path.
    Retries up to 3 times with exponential backoff on failure.
    """
    headers = {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    logger.info(f"Downloading PDF from {url} to {save_path}")
    
    try:
        with httpx.Client(follow_redirects=True, timeout=30.0, verify=False) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            
            # Basic validation that the content type is pdf or binary
            content_type = response.headers.get("content-type", "")
            if "html" in content_type.lower():
                logger.warning(f"URL returned HTML instead of a PDF file: {url}")
                raise DownloadError("URL returned HTML instead of a PDF.")
            
            with open(save_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=8192):
                    f.write(chunk)
                    
            logger.info("Download completed.")
            return True
            
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error during download: {e.response.status_code}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Request error during download: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise
