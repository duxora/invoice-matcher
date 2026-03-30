# Google Workspace Domain Provisioner — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Python script that adds a domain to Google Workspace (if not already present), configures DNS records via GoDaddy API, verifies the domain, and creates users via CLI arguments.

**Architecture:** Two API clients — GoDaddy REST (simple `requests` calls with API key auth) and Google Workspace Admin SDK (service account with domain-wide delegation). The script orchestrates: domain check → add domain → DNS setup (verification TXT + MX + SPF) → domain verification with retry → user creation. Single-file script with a thin config layer.

**Tech Stack:** Python 3.11+, `google-api-python-client`, `google-auth`, `requests`, `argparse`

**Prerequisites (manual one-time setup, not automated by this tool):**
1. GoDaddy account with 10+ domains (or Discount Domain Club) for API access
2. GoDaddy API key + secret from [developer.godaddy.com](https://developer.godaddy.com/)
3. Google Cloud project with Admin SDK API + Site Verification API enabled
4. Service account with JSON key file, configured for domain-wide delegation in Google Workspace Admin Console (`Security > API controls > Domain-wide Delegation`)
5. OAuth scopes granted: `admin.directory.domain`, `admin.directory.user`, `siteverification`

---

### Task 1: Project scaffold and dependencies

**Files:**
- Create: `workspace-provisioner/provision.py`
- Create: `workspace-provisioner/requirements.txt`

**Step 1: Create the project directory**

```bash
mkdir -p workspace-provisioner
```

**Step 2: Create requirements.txt**

```txt
google-api-python-client>=2.100.0
google-auth>=2.25.0
requests>=2.31.0
```

**Step 3: Create the initial script with argument parsing**

```python
#!/usr/bin/env python3
"""Google Workspace Domain Provisioner.

Adds a domain to Google Workspace, configures GoDaddy DNS,
verifies the domain, and creates users.

Usage:
    # Add domain + verify + setup DNS
    python provision.py setup-domain example.com

    # Create users on a verified domain
    python provision.py create-users example.com \
        "John Doe john" "Jane Smith jane"

    # Full flow: setup domain + create users
    python provision.py provision example.com \
        "John Doe john" "Jane Smith jane"

Environment variables:
    GODADDY_API_KEY       - GoDaddy API key
    GODADDY_API_SECRET    - GoDaddy API secret
    GOOGLE_SA_KEY_FILE    - Path to Google service account JSON key
    GOOGLE_ADMIN_EMAIL    - Super admin email for domain-wide delegation
"""
import argparse
import os
import sys
import time

import requests as http_requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --- Constants ---

GODADDY_BASE_URL = "https://api.godaddy.com"
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.domain",
    "https://www.googleapis.com/auth/admin.directory.user",
    "https://www.googleapis.com/auth/siteverification",
]
GOOGLE_MX_RECORDS = [
    {"data": "smtp.google.com", "name": "@", "ttl": 3600, "priority": 1, "type": "MX"},
]
GOOGLE_SPF_RECORD = "v=spf1 include:_spf.google.com ~all"
CUSTOMER_ID = "my_customer"


def main():
    parser = argparse.ArgumentParser(
        description="Google Workspace Domain Provisioner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # setup-domain
    sp_setup = subparsers.add_parser("setup-domain", help="Add domain to Workspace + configure DNS + verify")
    sp_setup.add_argument("domain", help="Domain name (e.g. example.com)")

    # create-users
    sp_users = subparsers.add_parser("create-users", help="Create users on a verified domain")
    sp_users.add_argument("domain", help="Domain name")
    sp_users.add_argument(
        "users",
        nargs="+",
        help='User specs: "FirstName LastName username" (e.g. "John Doe john" creates john@domain)',
    )
    sp_users.add_argument("--password", default=None, help="Default password (prompted if not set)")
    sp_users.add_argument("--change-password", action="store_true", default=True, help="Force password change on first login")

    # provision (full flow)
    sp_prov = subparsers.add_parser("provision", help="Full flow: setup domain + create users")
    sp_prov.add_argument("domain", help="Domain name")
    sp_prov.add_argument("users", nargs="+", help='User specs: "FirstName LastName username"')
    sp_prov.add_argument("--password", default=None, help="Default password (prompted if not set)")
    sp_prov.add_argument("--change-password", action="store_true", default=True, help="Force password change on first login")

    args = parser.parse_args()

    config = load_config()

    if args.command == "setup-domain":
        setup_domain(config, args.domain)
    elif args.command == "create-users":
        password = args.password or prompt_password()
        create_users(config, args.domain, args.users, password, args.change_password)
    elif args.command == "provision":
        password = args.password or prompt_password()
        setup_domain(config, args.domain)
        create_users(config, args.domain, args.users, password, args.change_password)


if __name__ == "__main__":
    main()
```

**Step 4: Verify the script parses arguments**

Run: `cd workspace-provisioner && python provision.py --help`
Expected: Help text with subcommands

**Step 5: Commit**

```bash
git add workspace-provisioner/
git commit -m "feat: scaffold workspace provisioner with arg parsing"
```

---

### Task 2: Configuration and Google API client setup

**Files:**
- Modify: `workspace-provisioner/provision.py`

**Step 1: Write the failing test — config loading with missing env vars**

Add above `main()`:

```python
def load_config():
    """Load configuration from environment variables."""
    required = {
        "GODADDY_API_KEY": "GoDaddy API key",
        "GODADDY_API_SECRET": "GoDaddy API secret",
        "GOOGLE_SA_KEY_FILE": "Path to Google service account JSON key file",
        "GOOGLE_ADMIN_EMAIL": "Google Workspace super admin email",
    }
    missing = [f"  {k} — {v}" for k, v in required.items() if not os.environ.get(k)]
    if missing:
        print("Missing required environment variables:", file=sys.stderr)
        print("\n".join(missing), file=sys.stderr)
        sys.exit(1)

    return {
        "godaddy_key": os.environ["GODADDY_API_KEY"],
        "godaddy_secret": os.environ["GODADDY_API_SECRET"],
        "google_sa_key_file": os.environ["GOOGLE_SA_KEY_FILE"],
        "google_admin_email": os.environ["GOOGLE_ADMIN_EMAIL"],
    }


def prompt_password():
    """Prompt for a password if not provided via CLI."""
    import getpass
    password = getpass.getpass("Default password for new users: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)
    return password
```

**Step 2: Run to verify config validation works**

Run: `python provision.py setup-domain test.com`
Expected: Error listing missing environment variables

**Step 3: Add Google API client builders**

Add after `load_config`:

```python
def build_google_services(config):
    """Build Google Admin SDK and Site Verification API clients."""
    credentials = service_account.Credentials.from_service_account_file(
        config["google_sa_key_file"],
        scopes=GOOGLE_SCOPES,
    )
    delegated = credentials.with_subject(config["google_admin_email"])

    admin = build("admin", "directory_v1", credentials=delegated, cache_discovery=False)
    verification = build("siteVerification", "v1", credentials=delegated, cache_discovery=False)
    return admin, verification


def godaddy_headers(config):
    """Return authorization headers for GoDaddy API."""
    return {
        "Authorization": f"sso-key {config['godaddy_key']}:{config['godaddy_secret']}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
```

**Step 4: Commit**

```bash
git add workspace-provisioner/provision.py
git commit -m "feat: add config loading and API client builders"
```

---

### Task 3: Domain check and add to Google Workspace

**Files:**
- Modify: `workspace-provisioner/provision.py`

**Step 1: Implement domain_exists and add_domain**

```python
def domain_exists_in_workspace(admin_service, domain):
    """Check if domain is already added to Google Workspace."""
    try:
        result = admin_service.domains().list(customer=CUSTOMER_ID).execute()
        domains = result.get("domains", [])
        return any(d["domainName"] == domain for d in domains)
    except HttpError as e:
        print(f"Error listing domains: {e}", file=sys.stderr)
        sys.exit(1)


def add_domain_to_workspace(admin_service, domain):
    """Add a domain to Google Workspace. Returns the domain resource."""
    try:
        result = admin_service.domains().insert(
            customer=CUSTOMER_ID,
            body={"domainName": domain},
        ).execute()
        print(f"Domain '{domain}' added to Google Workspace.")
        return result
    except HttpError as e:
        if e.resp.status == 409:
            print(f"Domain '{domain}' already exists in Workspace.")
            return None
        print(f"Error adding domain: {e}", file=sys.stderr)
        sys.exit(1)
```

**Step 2: Commit**

```bash
git add workspace-provisioner/provision.py
git commit -m "feat: add domain check and insert for Google Workspace"
```

---

### Task 4: GoDaddy DNS record management

**Files:**
- Modify: `workspace-provisioner/provision.py`

**Step 1: Implement GoDaddy DNS functions**

```python
def godaddy_add_txt_record(config, domain, value):
    """Add a TXT record to the domain via GoDaddy API (PATCH = append)."""
    url = f"{GODADDY_BASE_URL}/v1/domains/{domain}/records"
    payload = [{"data": value, "name": "@", "ttl": 3600, "type": "TXT"}]
    resp = http_requests.patch(url, json=payload, headers=godaddy_headers(config))
    if resp.status_code != 200:
        print(f"Error adding TXT record: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(f"TXT record added: {value[:50]}...")


def godaddy_set_mx_records(config, domain):
    """Replace MX records with Google Workspace MX via GoDaddy API."""
    url = f"{GODADDY_BASE_URL}/v1/domains/{domain}/records/MX"
    payload = [{"data": r["data"], "name": r["name"], "ttl": r["ttl"], "priority": r["priority"]} for r in GOOGLE_MX_RECORDS]
    resp = http_requests.put(url, json=payload, headers=godaddy_headers(config))
    if resp.status_code != 200:
        print(f"Error setting MX records: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print("MX records configured for Google Workspace.")


def godaddy_add_spf_record(config, domain):
    """Add SPF TXT record for Google Workspace email deliverability."""
    godaddy_add_txt_record(config, domain, GOOGLE_SPF_RECORD)
    print("SPF record added.")
```

**Step 2: Commit**

```bash
git add workspace-provisioner/provision.py
git commit -m "feat: add GoDaddy DNS record management (TXT, MX, SPF)"
```

---

### Task 5: Domain verification with retry

**Files:**
- Modify: `workspace-provisioner/provision.py`

**Step 1: Implement get_verification_token and verify_domain**

```python
def get_verification_token(verification_service, domain):
    """Get a DNS TXT verification token from Google Site Verification API."""
    try:
        result = verification_service.webResource().getToken(
            body={
                "site": {"type": "INET_DOMAIN", "identifier": domain},
                "verificationMethod": "DNS_TXT",
            }
        ).execute()
        return result["token"]
    except HttpError as e:
        print(f"Error getting verification token: {e}", file=sys.stderr)
        sys.exit(1)


def verify_domain(verification_service, domain, max_retries=10):
    """Verify domain ownership via DNS TXT record with exponential backoff."""
    for attempt in range(max_retries):
        try:
            result = verification_service.webResource().insert(
                verificationMethod="DNS_TXT",
                body={"site": {"type": "INET_DOMAIN", "identifier": domain}},
            ).execute()
            print(f"Domain '{domain}' verified successfully!")
            return result
        except HttpError as e:
            if e.resp.status == 400 and attempt < max_retries - 1:
                wait = min(2 ** attempt * 5, 300)  # 5s, 10s, 20s, ... max 5min
                print(f"DNS not propagated yet. Retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                print(f"Domain verification failed: {e}", file=sys.stderr)
                sys.exit(1)
```

**Step 2: Commit**

```bash
git add workspace-provisioner/provision.py
git commit -m "feat: add domain verification with exponential backoff"
```

---

### Task 6: setup_domain orchestration

**Files:**
- Modify: `workspace-provisioner/provision.py`

**Step 1: Implement the setup_domain function**

```python
def setup_domain(config, domain):
    """Full domain setup: add to Workspace, configure DNS, verify."""
    admin, verification = build_google_services(config)

    # 1. Check if domain already exists
    if domain_exists_in_workspace(admin, domain):
        print(f"Domain '{domain}' already in Google Workspace. Skipping add.")
    else:
        add_domain_to_workspace(admin, domain)

    # 2. Get verification token
    token = get_verification_token(verification, domain)
    print(f"Verification token: {token}")

    # 3. Add verification TXT record via GoDaddy
    godaddy_add_txt_record(config, domain, token)

    # 4. Set MX records for Gmail
    godaddy_set_mx_records(config, domain)

    # 5. Add SPF record
    godaddy_add_spf_record(config, domain)

    # 6. Wait a bit for DNS propagation, then verify
    print("Waiting 30s for initial DNS propagation...")
    time.sleep(30)
    verify_domain(verification, domain)

    print(f"\nDomain '{domain}' is fully set up in Google Workspace!")
```

**Step 2: Test with real credentials (manual)**

```bash
export GODADDY_API_KEY="your-key"
export GODADDY_API_SECRET="your-secret"
export GOOGLE_SA_KEY_FILE="/path/to/service-account.json"
export GOOGLE_ADMIN_EMAIL="admin@yourdomain.com"

python provision.py setup-domain testdomain.com
```

Expected: Domain added, DNS records configured, verification attempted

**Step 3: Commit**

```bash
git add workspace-provisioner/provision.py
git commit -m "feat: add setup_domain orchestration flow"
```

---

### Task 7: User creation

**Files:**
- Modify: `workspace-provisioner/provision.py`

**Step 1: Implement parse_user_spec and create_users**

```python
def parse_user_spec(spec, domain):
    """Parse 'FirstName LastName username' into user dict.

    Example: 'John Doe john' → john@domain with name John Doe
    """
    parts = spec.strip().split()
    if len(parts) < 3:
        print(f"Invalid user spec '{spec}'. Expected: 'FirstName LastName username'", file=sys.stderr)
        sys.exit(1)
    given_name = parts[0]
    family_name = " ".join(parts[1:-1])  # handle multi-word last names
    username = parts[-1]
    return {
        "primaryEmail": f"{username}@{domain}",
        "name": {"givenName": given_name, "familyName": family_name},
    }


def create_users(config, domain, user_specs, password, change_password=True):
    """Create multiple users on the domain."""
    admin, _ = build_google_services(config)

    for spec in user_specs:
        user = parse_user_spec(spec, domain)
        user["password"] = password
        user["changePasswordAtNextLogin"] = change_password

        try:
            result = admin.users().insert(body=user).execute()
            print(f"Created user: {result['primaryEmail']}")
        except HttpError as e:
            if e.resp.status == 409:
                print(f"User '{user['primaryEmail']}' already exists. Skipping.")
            else:
                print(f"Error creating user '{user['primaryEmail']}': {e}", file=sys.stderr)
```

**Step 2: Test user creation (manual, requires verified domain)**

```bash
python provision.py create-users yourdomain.com "John Doe john" "Jane Smith jane" --password "TempPass123!"
```

Expected: Users created or "already exists" messages

**Step 3: Commit**

```bash
git add workspace-provisioner/provision.py
git commit -m "feat: add batch user creation with CLI args"
```

---

### Task 8: Error handling, dry-run mode, and polish

**Files:**
- Modify: `workspace-provisioner/provision.py`

**Step 1: Add --dry-run flag to all subcommands**

In the argument parser, add to each subparser:

```python
# Add to sp_setup, sp_users, and sp_prov:
sp_setup.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
sp_users.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
sp_prov.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
```

**Step 2: Add dry-run checks in each action function**

Wrap each API call with a dry-run guard. Example pattern:

```python
# In setup_domain, accept dry_run param:
def setup_domain(config, domain, dry_run=False):
    admin, verification = build_google_services(config)

    if domain_exists_in_workspace(admin, domain):
        print(f"Domain '{domain}' already in Google Workspace. Skipping add.")
    else:
        if dry_run:
            print(f"[DRY RUN] Would add domain '{domain}' to Google Workspace")
        else:
            add_domain_to_workspace(admin, domain)

    token = get_verification_token(verification, domain)
    print(f"Verification token: {token}")

    if dry_run:
        print(f"[DRY RUN] Would add TXT record: {token}")
        print("[DRY RUN] Would set MX records for Google Workspace")
        print("[DRY RUN] Would add SPF record")
        print("[DRY RUN] Would attempt domain verification")
        return
    # ... rest of actual execution
```

Apply same pattern to `create_users`.

**Step 3: Update main() to pass dry_run**

```python
    if args.command == "setup-domain":
        setup_domain(config, args.domain, dry_run=args.dry_run)
    elif args.command == "create-users":
        password = args.password or (prompt_password() if not args.dry_run else "dry-run")
        create_users(config, args.domain, args.users, password, args.change_password, dry_run=args.dry_run)
    elif args.command == "provision":
        password = args.password or (prompt_password() if not args.dry_run else "dry-run")
        setup_domain(config, args.domain, dry_run=args.dry_run)
        create_users(config, args.domain, args.users, password, args.change_password, dry_run=args.dry_run)
```

**Step 4: Test dry-run**

Run: `python provision.py provision test.com "John Doe john" --dry-run`
Expected: `[DRY RUN]` prefixed messages, no actual API calls (except domain check + token fetch)

**Step 5: Commit**

```bash
git add workspace-provisioner/provision.py
git commit -m "feat: add dry-run mode for safe previews"
```

---

## GoDaddy API Access Warning

> **Important:** Since April 2024, GoDaddy requires **10+ active domains** on your account (or an active Discount Domain Club plan) to use the DNS Management API. Accounts with fewer domains will receive `403 Access Denied`. If this applies to you, consider:
> - Using a different DNS provider with friendlier API access (Cloudflare, Route53)
> - Manually setting DNS records and using only the Google Workspace parts of this tool

## Google Workspace MX Records Reference

The script uses the modern simplified MX record (post-April 2023):

| Priority | Server |
|----------|--------|
| 1 | `smtp.google.com` |

Legacy records (still supported, can be used if preferred):

| Priority | Server |
|----------|--------|
| 1 | `ASPMX.L.GOOGLE.COM` |
| 5 | `ALT1.ASPMX.L.GOOGLE.COM` |
| 5 | `ALT2.ASPMX.L.GOOGLE.COM` |
| 10 | `ALT3.ASPMX.L.GOOGLE.COM` |
| 10 | `ALT4.ASPMX.L.GOOGLE.COM` |
