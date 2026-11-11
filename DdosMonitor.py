import sqlite3
from datetime import datetime, timezone, timedelta
import time
from load_config import lire_config_yaml
from typing import Dict, Any, List


import requests



class DomainMonitor:
    def __init__(self, url, timeout=5):
        self.url = url
        self.timeout = timeout
        self.error_count = 0

    def check(self):
        """
        Check the domain by sending an HTTP GET request.
        """
        try:
            start = time.time()
            response = requests.get(self.url, timeout=self.timeout)
            latency = time.time() - start
            status = response.status_code

            if 500 <= status < 600:
                self.error_count += 1

            cdn_info = self.detect_cdn(response.headers)

            return DomainResult(self.url, status, latency, self.error_count, cdn_info, None)

        except requests.exceptions.Timeout:
            return DomainResult(self.url, None, None, self.error_count, None, "Timeout")

        except requests.exceptions.RequestException as e:
            return DomainResult(self.url, None, None, self.error_count, None, f"Error: {str(e)}")

    def detect_cdn(self, headers):
        """
        Detecting response headers that indicate the presence of a CDN.
        """
        cdn_headers = []
        for hdr in ['server', 'via', 'x-cache', 'x-cdn', 'cf-ray', 'cloudflare']:
            if hdr in headers:
                cdn_headers.append(f"{hdr}: {headers.get(hdr)}")
        return ', '.join(cdn_headers) if cdn_headers else "Not detected"

class DomainResult:
    def __init__(self, url, status, latency, error_count, cdn_info, error_msg):
        self.url = url
        self.status = status
        self.latency = latency
        self.error_count = error_count
        self.cdn_info = cdn_info
        self.error_msg = error_msg

    def __str__(self):
        if self.error_msg:
            return f"{self.url} | Erreur: {self.error_msg} | Errors cumulated: {self.error_count}"
        else:
            return (f"{self.url} | Status: {self.status} | Latency: {self.latency:.3f}s | "
                    f"Cumulated errors: {self.error_count} | CDN: {self.cdn_info}")






class DDosMonitorManager:
    def __init__(self, domain_list, interval=600, db_path='monitoring.db'):
        self.domains = [DomainMonitor(url) for url in domain_list]
        self.interval = interval
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS monitoring_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                status INTEGER,
                latency REAL,
                error_count INTEGER,
                cdn_info TEXT,
                error_msg TEXT,
                timestamp TEXT NOT NULL
            )
        ''')
        self.conn.commit()

    def save_result(self, result):
        self.cursor.execute('''
            INSERT INTO monitoring_results (
                url, status, latency, error_count, cdn_info, error_msg, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            result.url,
            result.status,
            result.latency,
            result.error_count,
            result.cdn_info,
            result.error_msg,
            datetime.now(timezone.utc).isoformat()

        ))
        self.conn.commit()


    def reset_database(self):
        """Clear all data from the monitoring database without deleting the file."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM monitoring_results;")
                print(f"Database '{self.db_path}' successfully cleared.")
        except Exception as e:
            print(f"Error while resetting database: {e}")


    def extract_metrics(self, window_minutes=10):
        window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        ws_iso = window_start.isoformat()

        #  Nombre erreurs par domaine
        self.cursor.execute('''
            SELECT url, COUNT(*) AS error_count
            FROM monitoring_results
            WHERE status BETWEEN 400 AND 599
            AND timestamp >= ?
            GROUP BY url
        ''', (ws_iso,))
        errors = self.cursor.fetchall()

        #  Latence moyenne par domaine
        self.cursor.execute('''
            SELECT url, AVG(latency) AS avg_latency
            FROM monitoring_results
            WHERE latency IS NOT NULL AND timestamp >= ?
            GROUP BY url
        ''', (ws_iso,))
        latencies = self.cursor.fetchall()

        return errors, latencies

    def fill_database(self, iterations=10, interval=20, save_full_response=True):
        for _ in range(iterations):
            results = [
                domain_monitor.check(save_full_response=save_full_response)
                for domain_monitor in self.domains
            ]
            self.save_results_batch(results)
            time.sleep(interval)



    def start(self):
        while True:
            print("\n--- Launching An iteration ---")
            for domain_monitor in self.domains:
                result = domain_monitor.check()
                print(result)
                self.save_result(result)
            time.sleep(self.interval)

    def __del__(self):
        self.conn.close()


def run_ddos_monitoring(config_path):
    config: Dict[str, Any] = lire_config_yaml(config_path)

    if not config:
        print("Critical Error: Load configuration failed. Exiting.")
        return

    domaines_a_monitorer: List[str] = config.get("Domains", [])

    intervalle_surveillance: int = config.get("Ddos_fetch_params", {}).get("collection_interval", 15)

    db_params: Dict[str, str] = config.get("database", {})
    db_path: str = db_params.get("path", "monitoring.db")

    if not domaines_a_monitorer:
         print("Warning: No domains configured for DDoS monitoring. Exiting.")
         return
    else:
         print(f"Loading {len(domaines_a_monitorer)} domaines.")

         manager = DDosMonitorManager(
             domain_list=domaines_a_monitorer,
             interval=intervalle_surveillance,
             db_path=db_path
         )

         manager.start()



if __name__ == "__main__":
    run_ddos_monitoring("Config/config.yaml")
