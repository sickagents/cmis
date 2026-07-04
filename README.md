# CMIS — Mistral API Key Farmer

Bulk create Mistral accounts, extract free API keys. Parallel workers + proxy support.

## Install

```bash
git clone https://github.com/sickagents/cmis.git
cd cmis
pip install -r requirements.txt
```

## Run

```bash
# Basic — 10 accounts, 1 worker
python3 cmis.py

# 50 accounts, 10 workers
python3 cmis.py -n 50 -w 10

# With proxy (Webshare rotating)
python3 cmis.py -n 100 -w 25 -p "http://user:pass@proxy:port"

# Custom output file
python3 cmis.py -n 200 -w 50 -o my_keys.txt
```

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `-n` | 10 | Number of accounts to create |
| `-w` | 1 | Parallel workers (max 100) |
| `-o` | result.txt | Output file for API keys |
| `-p` | (none) | Proxy URL (http/https/socks5) |

## Output

API keys saved to `result.txt` (one per line). Add to `.gitignore`.

## Proxy

Recommended: Webshare rotating proxy for bulk runs.

```bash
python3 cmis.py -n 500 -w 25 -p "http://user:pass@p.webshare.io:80"
```

Without proxy, rate limits hit faster (~10-15 concurrent from same IP).
