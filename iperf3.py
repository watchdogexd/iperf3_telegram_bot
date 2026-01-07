import asyncio
import ipaddress
import socket

from config import DEFAULT_PORT, DEFAULT_DURATION, DEFAULT_THREAD, DEFAULT_REVERSE, CHECK_PUBLIC_IP, IPERF3_PATH

if not IPERF3_PATH:
    IPERF3_PATH = "iperf3"

def resolve_host(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(
            host,
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )

        ips = {info[4][0] for info in infos}
        return list(ips)
    except socket.gaierror:
        return []
    
def is_public_ip(ip: str) -> bool:
    addr = ipaddress.ip_address(ip)
    return not (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
    )

def validate_host(host: str) -> tuple[bool, list[str] | None]:
    """
    only ipv4/ipv6 allowed here
    domains will be resolved separately
    """

    # ip format check 1
    try:
        ip = ipaddress.ip_address(host)
        if is_public_ip(str(ip)):
            return True, [str(ip)]
        return False, None
    except ValueError:
        pass
    
    # ip format check 2
    ips = resolve_host(host)
    if not ips:
        return False, None
    
    public_ips = [ip for ip in ips if is_public_ip(ip)]
    if not public_ips:
        return False, None

    return True, public_ips

def validate_port(port: int) -> bool:
    return 1 <= port <= 65535

async def run_iperf3(server=None, port=None, duration=None, thread=None, reverse=None) -> str:
    port = port or DEFAULT_PORT
    duration = duration or DEFAULT_DURATION
    thread = thread or DEFAULT_THREAD
    reverse = reverse if reverse is not None else DEFAULT_REVERSE

    if CHECK_PUBLIC_IP and not validate_host(server):
        return "invaild server. (only public ips allowed)"
    
    if not validate_port(port):
        return "invaild port. (1-65535)"

    cmd = [
        IPERF3_PATH,
        "-c", server,
        "-p", str(port),
        "-t", str(duration),
        "--connect-timeout", "3000",
    ]

    if reverse:
        cmd.append("-R")
    
    if thread and thread > 1:
        cmd.extend(["-P", str(thread)])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=duration + 5)

        if proc.returncode != 0:
            return f"iperf3 error:\n{stderr.decode()}"

        return stdout.decode()
    
    except asyncio.TimeoutError:
        return "iperf3 timeout"