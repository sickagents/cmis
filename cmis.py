#!/usr/bin/env python3
"""Mistral AI account farmer — parallel workers, API key output only."""

import argparse
import json
import random
import re
import string
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from curl_cffi import requests

lock = threading.Lock()
success_count = 0


class MailTM:
    def __init__(self):
        self.api_url = "https://api.mail.tm"
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update({
            "accept": "application/json",
            "content-type": "application/json",
        })
        self.token = None
        self.address = None
        self.password = f"Xq9!{self._rnd(12)}#Z"

    @staticmethod
    def _rnd(length=10):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))

    def create_account(self, retries=3):
        for attempt in range(retries):
            req = self.session.get(f"{self.api_url}/domains")
            if req.status_code == 200:
                break
            time.sleep(random.uniform(2, 5))
        else:
            return False
        try:
            data = req.json()
        except ValueError:
            return False
        domains = data if isinstance(data, list) else data.get("hydra:member", [])
        if not domains:
            return False
        domain = domains[0]["domain"]
        self.address = f"{self._rnd(8)}@{domain}"
        for attempt in range(3):
            req = self.session.post(
                f"{self.api_url}/accounts",
                json={"address": self.address, "password": self.password},
            )
            if req.status_code in (200, 201):
                return self._get_token()
            if req.status_code == 429:
                wait = random.uniform(5, 15)
                time.sleep(wait)
                continue
            time.sleep(random.uniform(1, 3))
        return False

    def _get_token(self):
        req = self.session.post(
            f"{self.api_url}/token",
            json={"address": self.address, "password": self.password},
        )
        try:
            if req.status_code == 200:
                self.token = req.json().get("token")
                self.session.headers["Authorization"] = f"Bearer {self.token}"
                return True
        except ValueError:
            pass
        return False

    def wait_for_otp(self, timeout=90):
        end = time.time() + timeout
        while time.time() < end:
            req = self.session.get(f"{self.api_url}/messages")
            try:
                if req.status_code == 200:
                    data = req.json()
                    msgs = data if isinstance(data, list) else data.get("hydra:member", [])
                    if msgs:
                        return self._extract_otp(msgs[0]["id"])
            except ValueError:
                pass
            time.sleep(3)
        return None

    def _extract_otp(self, msg_id):
        req = self.session.get(f"{self.api_url}/messages/{msg_id}")
        try:
            if req.status_code == 200:
                content = req.json().get("text", "")
                m = re.search(r"code=(\d{6})", content) or re.search(r"\b(\d{6})\b", content)
                if m:
                    return m.group(1)
        except ValueError:
            pass
        return None


class MistralBot:
    def __init__(self):
        self.session = requests.Session(impersonate="chrome120")
        self.base_url = "https://auth.mistral.ai"
        self.admin_url = "https://admin.mistral.ai"
        self.session.headers.update({
            "accept": "application/json",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/json",
            "origin": "https://v2.auth.mistral.ai",
            "referer": "https://v2.auth.mistral.ai/",
        })

    @staticmethod
    def _rnd(length=8):
        return "".join(random.choices(string.ascii_lowercase, k=length))

    @staticmethod
    def _csrf(nodes):
        for n in nodes:
            a = n.get("attributes", {})
            if a.get("name") == "csrf_token":
                return a.get("value")
        return None

    def register(self, email, password, first, last):
        url = (
            f"{self.base_url}/self-service/registration/browser"
            "?return_to=https%3A%2F%2Fconsole.mistral.ai%2Fhome"
            "&after_verification_return_to=https%3A%2F%2Fconsole.mistral.ai%2Fhome"
        )
        r = self.session.get(url)
        if r.status_code != 200:
            return False
        data = r.json()
        fid = data["id"]
        csrf = self._csrf(data["ui"]["nodes"])
        r2 = self.session.post(
            f"{self.base_url}/self-service/registration?flow={fid}",
            json={
                "csrf_token": csrf,
                "method": "password",
                "password": password,
                "traits": {"email": email, "name": {"first": first, "last": last}},
            },
        )
        if r2.status_code == 200:
            for a in r2.json().get("continue_with", []):
                if a.get("action") == "show_verification_ui":
                    return a["flow"]["id"]
            return True
        return False

    def verify_email(self, flow_id, otp):
        r = self.session.get(f"{self.base_url}/self-service/verification/flows?id={flow_id}")
        if r.status_code != 200:
            return False
        csrf = self._csrf(r.json()["ui"]["nodes"])
        r2 = self.session.post(
            f"{self.base_url}/self-service/verification?flow={flow_id}",
            json={"code": otp, "csrf_token": csrf, "method": "code"},
        )
        return r2.status_code == 200 and r2.json().get("state") == "passed_challenge"

    def create_organization(self):
        self.session.get(f"{self.admin_url}/join")
        csrf = self.session.cookies.get_dict().get("csrftoken", "")
        self.session.headers.update({
            "origin": self.admin_url,
            "referer": f"{self.admin_url}/join",
            "x-csrftoken": csrf,
        })
        r = self.session.post(
            f"{self.admin_url}/api/users/organizations",
            json={"name": self._rnd(8)},
        )
        return r.status_code in (200, 201)

    def get_workspace_uuid(self):
        csrf = self.session.cookies.get_dict().get("csrftoken", "")
        self.session.headers.update({
            "referer": f"{self.admin_url}/organization/api-keys",
            "x-csrftoken": csrf,
            "x-client": "settings-manager",
        })
        r = self.session.get(f"{self.admin_url}/api/workspaces?page=1&page_size=1000")
        if r.status_code == 200:
            items = r.json().get("items", [])
            if items:
                return items[0].get("uuid")
        return None

    def create_api_key(self, ws_uuid):
        self.session.headers["referer"] = f"{self.admin_url}/organization/api-keys"
        r = self.session.post(
            f"{self.admin_url}/api/billing/api-keys",
            json={
                "name": self._rnd(8),
                "workspace_uuid": ws_uuid,
                "primitive_access_scope": "shared_only",
            },
        )
        if r.status_code in (200, 201):
            return r.json().get("key")
        return None


def run_one(worker_id: int, output_file: str) -> bool:
    """Run one account creation cycle. Returns True if API key obtained."""
    global success_count
    try:
        # Stagger start to avoid rate limit
        time.sleep(random.uniform(0, 3))
        mail = MailTM()
        if not mail.create_account():
            print(f"  [W{worker_id:02d}] Email creation failed")
            return False

        bot = MistralBot()
        fn, ln = mail._rnd(6), mail._rnd(6)

        vf = bot.register(mail.address, mail.password, fn, ln)
        if not vf or not isinstance(vf, str):
            print(f"  [W{worker_id:02d}] Registration failed")
            return False

        otp = mail.wait_for_otp()
        if not otp:
            print(f"  [W{worker_id:02d}] OTP timeout")
            return False

        if not bot.verify_email(vf, otp):
            print(f"  [W{worker_id:02d}] Verification failed")
            return False

        if not bot.create_organization():
            print(f"  [W{worker_id:02d}] Org creation failed")
            return False

        ws = bot.get_workspace_uuid()
        if not ws:
            print(f"  [W{worker_id:02d}] Workspace not found")
            return False

        key = bot.create_api_key(ws)
        if not key:
            print(f"  [W{worker_id:02d}] API key creation failed")
            return False

        with lock:
            success_count += 1
            n = success_count
            with open(output_file, "a") as f:
                f.write(f"{key}\n")

        print(f"  [W{worker_id:02d}] #{n} OK — {key[:24]}...")
        return True

    except Exception as e:
        print(f"  [W{worker_id:02d}] Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Mistral API Key Farmer")
    parser.add_argument("-n", "--count", type=int, default=10, help="Number of accounts")
    parser.add_argument("-w", "--workers", type=int, default=1, help="Parallel workers (max 50)")
    parser.add_argument("-o", "--output", type=str, default="result.txt", help="Output file")
    args = parser.parse_args()

    workers = min(args.workers, 50)
    count = args.count

    print(f"{'=' * 55}")
    print(f"  CMIS — Mistral API Key Farmer")
    print(f"  Target: {count} keys | Workers: {workers}")
    print(f"  Output: {args.output}")
    print(f"{'=' * 55}\n")

    global success_count
    success_count = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {}
        submitted = 0

        # Submit initial batch
        for i in range(min(count, workers)):
            futures[pool.submit(run_one, i + 1, args.output)] = i + 1
            submitted += 1

        # Refill as workers finish
        while futures:
            done_fut = next(as_completed(futures))
            wid = futures.pop(done_fut)
            ok = done_fut.result()
            if not ok:
                failed += 1

            if submitted < count:
                futures[pool.submit(run_one, wid, args.output)] = wid
                submitted += 1

    print(f"\n{'=' * 55}")
    print(f"  Done: {success_count} keys saved | {failed} failed")
    print(f"  Output: {args.output}")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    main()
