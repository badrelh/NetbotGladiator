import requests
import socket
import difflib
from typing import Dict, Any, List
import time
from pathlib import Path

from load_config import lire_config_yaml
from notify import send_email


SEUIL_DEFACEMENT = 50
class WebDefacementDetector:
    def __init__(self, domain, interval, timeout=10):
        self.domain = domain
        self.timeout = timeout
        self.interval = interval
        self.original_snapshot = self.fetch_page()

    def fetch_page(self):
        try:
            url = f"{self.domain}"
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                return resp.text
            else:
                print(f"Error occured during loading page {self.domain}, statut: {resp.status_code}")
        except Exception as e:
            print(f"Fetch Error : {e}")
        return ""

    def is_defaced(self, current_html):
        diff = list(difflib.unified_diff(self.original_snapshot.splitlines(), current_html.splitlines()))
        num_diff = len(diff)
        if num_diff > SEUIL_DEFACEMENT:
            return True, num_diff
        return False, num_diff

    def check_defacement_by_diff(self):
        current_html = self.fetch_page()
        if not current_html:
            print(f"Inaccessible page {self.domain}")
            return False, 0
        return self.is_defaced(current_html)


class DomainDefacementMonitor:
    def __init__(self, domain, config_path=None, interval=600):
        self.domain = domain
        self.web_detector = WebDefacementDetector(domain, interval)
        self.interval = interval
        config_path = config_path or "Config/config.yaml"

    def run_cycle(self):
        print(f"Monitoring {self.domain}...")
        is_defaced, num_diff = self.web_detector.check_defacement_by_diff()
        if is_defaced:
            notify_msg = f"Defacement detected on {self.domain} with {num_diff} different sequences."
            send_email(
                subject=f"[ALERT] Defacement detected on {self.domain}",
                body=notify_msg,
                config_path=self.config_path
            )
            print(f"[ALERT] Defacement detected! [{num_diff}] different sequences")
        else:
            print(f"[OK] No defacement detected [{num_diff}] sequences")

    def run(self, once=False):
        if once:
            print(f"Running single cycle for {self.domain}...")
            self.run_cycle()
        else:
            print(f"Starting continuous monitoring for {self.domain}...")
            try:
                self.run_cycle()
                print(f"Next check in {self.interval}s...\n")

            except KeyboardInterrupt:
                print(f"\nMonitoring stopped for {self.domain}")


def run_defacement_monitoring(config_path, once=False):
    if not Path(config_path).exists():
        print(f"Error: Config file not found: {config_path}")
        return
    config: Dict[str, Any] = lire_config_yaml(config_path)
    if not config:
        print("Error: Cannot load configuration.")
        return
    domains: List[str] = config.get("Domains", [])
    interval: int = config.get("Defacement_fetch_params", {}).get("interval", 600)

    if not domains:
        print("Error: No domains found in configuration.")
        return
    print(f"Loading {len(domains)} domain(s).")
    while True:
        for domain in domains:
            print(f"\n--- Starting monitor for {domain} ---")
            monitor = DomainDefacementMonitor(domain,config_path, interval)
            monitor.run(once=True)
        if once:
            return
        time.sleep(interval)

if __name__ == "__main__":
    run_defacement_monitoring("Config/config.yaml")
