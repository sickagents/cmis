# cmis

Mistral AI account farmer — parallel workers, API key output only.

## What It Does

1. Create temp email via mail.tm
2. Register Mistral AI account
3. Verify email via OTP
4. Create organization + workspace
5. Generate API key
6. Save API key to `result.txt`

## Installation

```bash
pip install curl_cffi
```

## Usage

```bash
# 1 account, sequential
python cmis.py -n 1

# 10 accounts, 5 parallel workers
python cmis.py -n 10 -w 5

# 100 accounts, 20 workers (160 vCPU VPS)
python cmis.py -n 100 -w 20

# Custom output file
python cmis.py -n 50 -w 10 -o keys.txt
```

## Worker Recommendations

| VPS Spec | Workers | Expected Speed |
|---|---|---|
| 2-4 vCPU | 1-2 | ~1 key/min |
| 8-16 vCPU | 3-8 | ~3-8 keys/min |
| 32-64 vCPU | 10-20 | ~10-20 keys/min |
| 128-160 vCPU | 20-40 | ~20-40 keys/min |

## Output

`result.txt` — one API key per line:

```
sk-abc123xyz...
sk-def456xyz...
sk-ghi789xyz...
```
