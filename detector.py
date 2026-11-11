import sqlite3
import requests
import statistics
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from load_config import lire_config_yaml
from notify import send_email

class BehaviorAnomalyDetector:
    def __init__(self, db_path: str, config: Dict[str, Any]):
        self.db_path = db_path
        self.config = config or {}
        self.params = self.config.get("Ddos_fetch_params", {})
        self.window_minutes = int(self.params.get("window_minutes", 60))
        self.timeout = int(self.params.get("timeout", 10))
        self.min_samples = int(self.params.get("min_samples", 5))
        self.latency_factor = float(self.params.get("latency_factor", 1.5))
        self.std_multiplier = float(self.params.get("std_multiplier", 2.0))
        self.error_multiplier = float(self.params.get("error_multiplier", 2.0))
        self.min_error_threshold = int(self.params.get("min_error_threshold", 3))

    def check_domain(self, url: str):
        """
        Perform an active request to `url`, compare to baseline derived from
        the last `window_minutes` of records in the database, and decide if an alert is required.
        """
        try:
            resp = requests.get(url, timeout=self.timeout)
            new_status = resp.status_code
            new_latency = resp.elapsed.total_seconds()
        except Exception as e:
            # network-level failure => alert
            message = f"Domain: {url}\nConnection failure: {e}"
            self._send_alert(url, message)
            return

        # load recent history
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        window_start = datetime.now(timezone.utc) - timedelta(minutes=self.window_minutes)
        ws_iso = window_start.isoformat()

        cur.execute("""
            SELECT latency, status, error_count
            FROM monitoring_results
            WHERE url = ? AND timestamp >= ?
            AND latency IS NOT NULL
            ORDER BY timestamp DESC
        """, (url, ws_iso))
        rows = cur.fetchall()
        conn.close()

        if len(rows) < self.min_samples:
            # Not enough history to compute a reliable baseline
            print(f"[INFO] {url}: insufficient history ({len(rows)} samples). Skipping anomaly decision.")
            return

        latencies = [r[0] for r in rows if r[0] is not None]
        statuses = [r[1] for r in rows]
        error_counts = [r[2] if len(r) > 2 and r[2] is not None else 0 for r in rows]

        baseline_avg = statistics.mean(latencies)
        baseline_std = statistics.pstdev(latencies) if len(latencies) > 1 else 0.0
        baseline_error_avg = statistics.mean(error_counts) if error_counts else 0.0

        # threshold options: choose more robust rule using std if available
        max_expected_latency = max(self.latency_factor * baseline_avg, baseline_avg + self.std_multiplier * baseline_std)

        is_latency_abnormal = new_latency > max_expected_latency
        is_error_status = 400 <= new_status <= 599

        # error detection using baseline errors
        recent_error_count = sum(1 for s in statuses if 400 <= s <= 599)
        error_anomaly = False
        if baseline_error_avg < 1:
            if recent_error_count >= self.min_error_threshold:
                error_anomaly = True
        else:
            if recent_error_count > self.error_multiplier * baseline_error_avg:
                error_anomaly = True

        if is_latency_abnormal or is_error_status or error_anomaly:
            msg = self._format_alert(
                url=url,
                observed_status=new_status,
                observed_latency=new_latency,
                baseline_avg=baseline_avg,
                baseline_std=baseline_std,
                recent_samples=len(rows),
                recent_errors=recent_error_count,
                baseline_errors=baseline_error_avg
            )
            print(msg)
            self._send_alert(url, msg)
        else:
            print(f"[OK] {url}: latency={new_latency:.3f}s within baseline (avg={baseline_avg:.3f}s).")

    def _format_alert(self, url, observed_status, observed_latency, baseline_avg, baseline_std, recent_samples, recent_errors, baseline_errors):
        lines = [
            f"Domain: {url}",
            f"Observed HTTP status: {observed_status}",
            f"Observed latency: {observed_latency:.3f} s",
            f"Baseline latency: {baseline_avg:.3f} s (std={baseline_std:.3f}) based on {recent_samples} samples",
            f"Recent HTTP error count in window: {recent_errors}",
            f"Baseline average error count: {baseline_errors:.3f}",
            "Decision: abnormal behavior detected based on baseline comparison."
        ]
        return "\n".join(lines)

    def _send_alert(self, url, message, config_path='Config/config.yaml'):
        subject = f"[DDoS Alert] Abnormal behavior detected on {url}"
        send_email( subject, message, config_path=config_path)

def run_ddos_detect(config_path):
    config = lire_config_yaml(config_path)
    db_path = config.get("database", {}).get("path", "monitoring.db")
    detector = BehaviorAnomalyDetector(db_path=db_path, config=config)
    domains = config.get("Domains", [])
    for d in domains:
        detector.check_domain(d)




if __name__ == "__main__":
    config_path = "Config/config.yaml"
    config = lire_config_yaml(config_path)
    db_path = config.get("database", {}).get("path", "monitoring.db")
    detector = BehaviorAnomalyDetector(db_path=db_path, config=config)
    domains = config.get("Domains", [])
    for d in domains:
        detector.check_domain(d)
