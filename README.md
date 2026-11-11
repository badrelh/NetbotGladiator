# NetBotGladiator

NetBotGladiator is a lightweight monitoring suite for:
- **DDoS / availability monitoring** (latency, HTTP status)
- **Web defacement detection** (HTML diff)
- **TLS certificate expiration checks**
- **Baseline-based anomaly detection**
- **Email alerts** for abnormal behavior

---

## ⚙️ Configuration

Main configuration file: `Config/config.yaml`

```yaml
Domains:
  - "https://www.example.com"
  - "https://www.google.com"

Ddos_fetch_params:
  timeout: 10                   # Maximum time (in seconds) to wait for an HTTP response
  collection_interval: 15       # Interval (in seconds) between each request used to collect and store metrics in the database
  interval: 600                 # Time (in seconds) between full detection cycles when monitoring continuously
  window_minutes: 60            # Defines the time window (in minutes) of historical data used to compute the average (baseline)
  latency_factor: 1.5           # New latency is considered abnormal if it exceeds 1.5 × the historical average
  min_samples: 10               # minimal historical samples required to decide
  std_multiplier: 2             # Additional threshold: new latency is abnormal if above average + 2 × standard deviation
  error_multiplier: 2           # Detects anomaly if recent HTTP error count exceeds twice the historical error average
  min_error_threshold: 3        # If baseline error rate is almost zero, an alert is triggered if 3 or more recent errors occur

Defacement_fetch_params:
  timeout: 10                   # Timeout (in seconds) for each request during defacement check
  interval: 3600                # Interval (in seconds) between two HTML comparisons for the same domain (default: once per hour)

certificates:
  port: 443                     # TCP port used for SSL/TLS certificate checks (default HTTPS port)
  alert_threshold_days: 21      # Trigger alert if certificate expiration is within 21 days
  interval: 86400               # Interval (in seconds) between certificate checks (default: every 24 hours)

database:
  path: "monitoring.db"         # Path to the SQLite database used for storing monitoring results

email_config:
  smtp_server: "smtp.gmail.com" # SMTP server address (e.g., Gmail)
  smtp_port: 587                # SMTP port (587 for TLS)
  sender_email: "user@example.com" # Sender email address used to send notifications
  sender_password: "APP_PASSWORD"  # SMTP or app-specific password (use an App Password for Gmail)
  default_receiver: "receiver@example.com" # Default alert recipient (can be changed dynamically)

```


## 🚀 Installation

````bash
git clone <repository_url>
cd NetBotGladiator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
````

---

## 🧩 Usage

Run each monitoring service using the CLI (`app.py`):

```bash
# Run Behavior collector (Run collecting behavior metrics)
python3 app.py collector -c Config/config.yaml

# Run ddos detector (Run detecting cycles)
python3 app.py ddos_detect -c Config/config.yaml


# Defacement detection (Run detecting cycles )
python3 app.py defacement -c Config/config.yaml


# Certificate expiration monitoring (checks the certification expiration)
python3 app.py certificats -c Config/config.yaml

# Run all services concurrently (Runs all the plug-ins)
python3 app.py all -c Config/config.yaml

```

Run the anomaly detector (baseline comparison):

```bash
python3 detector.py
```

---

## 👥 Auteurs

- **Badr El Habbassi** : [@badrelh](https://github.com/badrelh)
- **Aymane Bouyghf** : [@aymane-03-cs](https://github.com/aymane-03-cs)
