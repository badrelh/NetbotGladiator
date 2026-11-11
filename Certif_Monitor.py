
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse
from load_config import lire_config_yaml
from notify import send_email
import ssl
import socket
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import time


def _normalize_host(value: str) -> Tuple[str, Optional[int]]:
    parsed = urlparse(value if "://" in value else f"//{value}")
    return parsed.hostname, parsed.port
@dataclass
class CertificateResult:
    hostname: str
    port: int
    expiry: Optional[datetime]
    days_remaining: Optional[int]
    error: Optional[str] = None

class CertificateChecker:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def get_cert_expiry(self, hostname: str, port: int = 443) -> datetime:
        ctx = ssl.create_default_context()

        with socket.create_connection((hostname, port), timeout=self.timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                if not cert or "notAfter" not in cert:
                    raise RuntimeError("Certificate data unavailable")

                not_after = cert.get("notAfter")
                ts = ssl.cert_time_to_seconds(not_after)
                expiry = datetime.fromtimestamp(ts, tz=timezone.utc)
                return expiry




class CertifMonitor:
    def __init__(self, config_file: str, checker: Optional[CertificateChecker] = None):
        self.config_file = config_file
        self.checker = checker or CertificateChecker()
        self.last_alerts: Dict[str, datetime] = {} # Avoid spam , and adding a cooldown interval to send mail

    def _load_config(self) -> Dict[str, Any]:
        return lire_config_yaml(self.config_file) or {}

    def start_monitoring(self, once: bool = False) -> List[CertificateResult]:

        cfg = self._load_config()
        domaines_bruts: List[str] = (
            cfg.get("certificates", {}).get("domains", cfg.get("Domains", []))
        )
        domaines_a_monitorer = [_normalize_host(x) for x in domaines_bruts]

        threshold = cfg.get("certificates", {}).get("alert_threshold_days", 30)
        port = cfg.get("certificates", {}).get("port", 443)
        interval = cfg.get("certificates", {}).get("interval", 3600*24)

        if not domaines_a_monitorer:
            print("No domains configured for certificate monitoring.")
            return []

        try:
            if once:
                print("Running single certificate check...\n")
                return self._check_cycle(domaines_a_monitorer, port, threshold)
            else:
                print("Starting continuous certificate monitoring...\n")
                while True:
                    _ = self._check_cycle(domaines_a_monitorer, port, threshold)
                    print(f"Next check in {interval}s...\n", flush=True)
                    time.sleep(interval)
        except KeyboardInterrupt:
            print("\nCertificate monitoring stopped")
            return []


    def _check_cycle(self, domains: List[str], port: int, threshold: int) -> List[CertificateResult]:
        results: List[CertificateResult] = []
        alerts = []
        now = datetime.now(timezone.utc)
        cooldown = timedelta(hours=24)

        for host_tuple in domains:
            hostname, custom_port = host_tuple
            current_port = custom_port or port
            print(f"Checking {hostname}:{current_port}...", flush=True)
            try:
                expiry = self.checker.get_cert_expiry(hostname, port=current_port)
                delta = expiry - now
                days = int(delta.total_seconds() // 86400)
                results.append(CertificateResult(hostname, current_port, expiry, days))

                if days < 0:
                    level = "CRITICAL"
                elif days <= threshold:
                    level = "WARNING"
                else:
                    level = None

                if level:
                    print(f"[ALERT]  {hostname}:{current_port} expires in {days} days (on {expiry})", flush=True)
                    last_sent = self.last_alerts.get(hostname)
                    if not last_sent or (now - last_sent) > cooldown:
                        alerts.append((level, hostname, current_port, days, expiry))
                        self.last_alerts[hostname] = now
                else:
                    print(f"[OK] {hostname}:{current_port} certificate valid for {days} days (expires on {expiry})", flush=True)

            except Exception as e:
                print(f"[ERROR] {hostname}:{current_port}: {str(e)}", flush=True)
                results.append(CertificateResult(hostname, current_port, None, None, error=str(e)))

        if alerts:
            body = "\n".join(f"{lvl} {hostname}:{port} -> {days} days (expiry: {expiry})" for lvl, hostname, days, expiry in alerts)
            send_email(subject="Certificate monitor alerts", body=body, config_path=self.config_file)

        return results





def run_certifs_monitoring(config_path: str, once: bool = False):
    monitor = CertifMonitor(config_path)
    monitor.start_monitoring(once=once)
