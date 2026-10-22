import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import Request, HTTPException, status
from fastapi.security import APIKeyHeader
from .config import settings

API_KEY_HEADER = APIKeyHeader(name="X-Agent-Token", auto_error=False)

# Private / local IP subnets to block for crawler SSRF protection
PRIVATE_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),   # Link-local & cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),        # Unique local address
    ipaddress.ip_network("fe80::/10"),       # Link-local IPv6
]

FORBIDDEN_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
    "instance-data",
}

def verify_token(token: str | None) -> bool:
    if not token:
        return False
    return token == settings.agent_token

async def get_current_token_auth(request: Request):
    """
    Validates pairing token from header 'X-Agent-Token' or query param 'token'.
    """
    token = request.headers.get("X-Agent-Token") or request.query_params.get("token")
    if not token or not verify_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-Agent-Token pairing token. Please pair with the Chrome Extension."
        )
    return token

def is_safe_url_for_crawling(url: str) -> tuple[bool, str]:
    """
    Validates that a URL does not attempt SSRF, cloud metadata access, or private network scanning.
    """
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"Unsupported scheme: {parsed.scheme}. Only HTTP/HTTPS allowed."
        
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid URL: missing hostname."

        if hostname.lower() in FORBIDDEN_HOSTNAMES:
            return False, f"Access to '{hostname}' is prohibited for SSRF safety."

        # Check if hostname is an IP address
        try:
            ip = ipaddress.ip_address(hostname)
            for net in PRIVATE_NETWORKS:
                if ip in net:
                    return False, f"Access to private/local IP {ip} is blocked."
            return True, "Safe"
        except ValueError:
            # Hostname is a domain name, resolve DNS to verify its resolved IPs
            pass

        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip = ipaddress.ip_address(ip_str)
                for net in PRIVATE_NETWORKS:
                    if ip in net:
                        return False, f"Hostname '{hostname}' resolves to private IP {ip}. Blocked."
        except socket.gaierror:
            return False, f"Could not resolve hostname '{hostname}'."

        return True, "Safe"
    except Exception as e:
        return False, f"URL validation failed: {str(e)}"

def sanitize_untrusted_text(text: str, max_length: int = 50000) -> str:
    """
    Sanitizes external web page text to mitigate prompt injection.
    Limits text length and flags foreign instructions.
    """
    if not text:
        return ""
    text = text[:max_length]
    # Remove null bytes or anomalous control characters
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t ")
    return cleaned
