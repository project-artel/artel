import base64
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ENV = dict(line.split("=", 1) for line in (ROOT / ".env").read_text().splitlines()
           if line.strip() and not line.lstrip().startswith("#"))
ACCOUNT = "http://127.0.0.1:" + ENV["ACCOUNT_PORT"]


def request(path, body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {} if body is None else {"Content-Type": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(ACCOUNT + path, data, headers), timeout=5) as reply:
        return json.load(reply)


def wait_for_account():
    for _ in range(60):
        try:
            if request("/.well-known/jwks")["keys"]:
                return
        except OSError:
            pass
        time.sleep(2)
    raise SystemExit("Account server JWKS did not become ready")


def create_or_login(email, name):
    credentials = {"email": email, "password": ENV["QA_ACCOUNT_PASSWORD"]}
    try:
        token = request("/api/members/login", credentials)["jwt"]
    except urllib.error.HTTPError as error:
        if error.code not in (400, 401, 403, 404):
            raise
        token = request("/api/members", {**credentials, "name": name})["jwt"]
    payload = token.split(".")[1]
    return int(json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))["memberId"])


def main():
    wait_for_account()
    expected_ids = [int(value) for value in ENV["QA_ACCOUNTS"].split(",")]
    if len(expected_ids) != 2:
        raise SystemExit("QA_ACCOUNTS must contain the two sample account IDs")
    for number, expected_id in enumerate(expected_ids, start=1):
        email = f"qa{number}@arcanecasters.test"
        account_id = create_or_login(email, f"ARTEL QA {number}")
        if account_id != expected_id:
            raise SystemExit(f"{email} has memberId={account_id}, expected {expected_id}. Update QA_ACCOUNTS and recreate Lobby and Game.")
        with (ROOT / "qa" / "seed-deck.sql").open("rb") as sql:
            subprocess.run(["docker", "compose", "exec", "-T", "postgres", "psql",
                            "-U", "qa", "-d", "game", "-v", "ON_ERROR_STOP=1",
                            "-v", f"account_id={account_id}", "-v", f"bot_id={int(ENV['QA_BOT_ID'])}"],
                           cwd=ROOT, stdin=sql, check=True, stdout=subprocess.DEVNULL)
        print(f"{email} ready (memberId={account_id})")


if __name__ == "__main__":
    main()
