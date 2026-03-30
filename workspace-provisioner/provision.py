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
import getpass
import hashlib
import os
import pathlib
import sys
import time

import requests as http_requests
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# --- Constants ---

GODADDY_BASE_URL = os.environ.get("GODADDY_BASE_URL", "https://api.ote-godaddy.com")
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
GODADDY_TIMEOUT = (10, 30)  # (connect, read) seconds


# --- Configuration ---

ENV_FILE_SEARCH_PATHS = [
    pathlib.Path.cwd() / ".env",
    pathlib.Path.home() / ".config" / "wsp" / ".env",
]


def load_env_file():
    """Auto-load .env file from cwd or ~/.config/wsp/.env."""
    for path in ENV_FILE_SEARCH_PATHS:
        if path.is_file():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Strip optional 'export ' prefix
                    if line.startswith("export "):
                        line = line[7:]
                    key, _, value = line.partition("=")
                    if key and value:
                        os.environ.setdefault(key.strip(), value.strip())
            print(f"Loaded config from {path}")
            return
    # No .env found — that's fine, env vars may be set directly


def load_config(dry_run=False):
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

    key_file = os.environ["GOOGLE_SA_KEY_FILE"]
    if not dry_run and not os.path.isfile(key_file):
        print(f"GOOGLE_SA_KEY_FILE not found: {key_file}", file=sys.stderr)
        sys.exit(1)

    return {
        "godaddy_key": os.environ["GODADDY_API_KEY"],
        "godaddy_secret": os.environ["GODADDY_API_SECRET"],
        "google_sa_key_file": key_file,
        "google_admin_email": os.environ["GOOGLE_ADMIN_EMAIL"],
    }


def prompt_password():
    """Prompt for a password if not provided via CLI."""
    password = getpass.getpass("Default password for new users: ")
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)
    return password


# --- API Clients ---

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


# --- Google Workspace Domain Management ---

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


# --- GoDaddy DNS Management ---

def godaddy_add_txt_record(config, domain, value):
    """Add a TXT record to the domain via GoDaddy API (PATCH = append)."""
    url = f"{GODADDY_BASE_URL}/v1/domains/{domain}/records"
    payload = [{"data": value, "name": "@", "ttl": 3600, "type": "TXT"}]
    resp = http_requests.patch(url, json=payload, headers=godaddy_headers(config), timeout=GODADDY_TIMEOUT)
    if resp.status_code != 200:
        print(f"Error adding TXT record: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print(f"TXT record added: {value[:50]}...")


def godaddy_set_mx_records(config, domain):
    """Replace MX records with Google Workspace MX via GoDaddy API."""
    url = f"{GODADDY_BASE_URL}/v1/domains/{domain}/records/MX"
    payload = [
        {"data": r["data"], "name": r["name"], "ttl": r["ttl"], "priority": r["priority"]}
        for r in GOOGLE_MX_RECORDS
    ]
    resp = http_requests.put(url, json=payload, headers=godaddy_headers(config), timeout=GODADDY_TIMEOUT)
    if resp.status_code != 200:
        print(f"Error setting MX records: {resp.status_code} {resp.text}", file=sys.stderr)
        sys.exit(1)
    print("MX records configured for Google Workspace.")


def godaddy_add_spf_record(config, domain):
    """Add SPF TXT record for Google Workspace email deliverability."""
    godaddy_add_txt_record(config, domain, GOOGLE_SPF_RECORD)


# --- Domain Verification ---

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
                wait = min(2 ** attempt * 5, 300)
                print(f"DNS not propagated yet. Retrying in {wait}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait)
            else:
                print(f"Domain verification failed: {e}", file=sys.stderr)
                sys.exit(1)


# --- Orchestration ---

def setup_domain(config, domain, dry_run=False):
    """Full domain setup: add to Workspace, configure DNS, verify.

    Returns (admin_service, verification_service) for reuse by callers.
    In dry_run mode, returns (None, None).
    """
    if dry_run:
        print(f"[DRY RUN] Would check if domain '{domain}' exists in Google Workspace")
        print(f"[DRY RUN] Would add domain '{domain}' to Google Workspace (if not present)")
        print(f"[DRY RUN] Would get DNS verification token from Google")
        print(f"[DRY RUN] Would add TXT verification record via GoDaddy")
        print("[DRY RUN] Would set MX records for Google Workspace (smtp.google.com)")
        print("[DRY RUN] Would add SPF TXT record")
        print("[DRY RUN] Would verify domain ownership via DNS")
        return None, None

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

    # 6. Wait for DNS propagation, then verify
    print("Waiting 30s for initial DNS propagation...")
    time.sleep(30)
    verify_domain(verification, domain)

    print(f"\nDomain '{domain}' is fully set up in Google Workspace!")
    return admin, verification


# --- User Listing ---

def list_users(config, domain):
    """List all users on a domain."""
    admin, _ = build_google_services(config)

    try:
        users = []
        request = admin.users().list(domain=domain, maxResults=500, orderBy="email")
        while request:
            result = request.execute()
            users.extend(result.get("users", []))
            request = admin.users().list_next(request, result)

        if not users:
            print(f"No users found on '{domain}'.")
            return

        print(f"\nUsers on '{domain}' ({len(users)}):\n")
        print(f"{'Email':<40} {'Name':<30} {'Status':<12} {'Admin'}")
        print("-" * 95)
        for u in users:
            email = u.get("primaryEmail", "")
            name = u.get("name", {})
            full_name = f"{name.get('givenName', '')} {name.get('familyName', '')}"
            status = "Suspended" if u.get("suspended") else "Active"
            is_admin = "Yes" if u.get("isAdmin") else ""
            print(f"{email:<40} {full_name:<30} {status:<12} {is_admin}")

    except HttpError as e:
        print(f"Error listing users: {e}", file=sys.stderr)
        sys.exit(1)


# --- User Creation ---

def parse_user_spec(spec, domain):
    """Parse 'FirstName LastName username' into user dict.

    Example: 'John Doe john' -> john@domain with name John Doe
    """
    parts = spec.strip().split()
    if len(parts) < 3:
        print(f"Invalid user spec '{spec}'. Expected: 'FirstName LastName username'", file=sys.stderr)
        sys.exit(1)
    given_name = parts[0]
    family_name = " ".join(parts[1:-1])
    username = parts[-1]
    return {
        "primaryEmail": f"{username}@{domain}",
        "name": {"givenName": given_name, "familyName": family_name},
    }


def create_users(config, domain, user_specs, password, change_password=True, admin_service=None, dry_run=False):
    """Create multiple users on the domain."""
    if not dry_run and admin_service is None:
        admin_service, _ = build_google_services(config)

    hashed_password = hashlib.sha1(password.encode()).hexdigest()
    failures = []

    for spec in user_specs:
        user = parse_user_spec(spec, domain)
        user["password"] = hashed_password
        user["hashFunction"] = "SHA-1"
        user["changePasswordAtNextLogin"] = change_password

        if dry_run:
            print(f"[DRY RUN] Would create user: {user['primaryEmail']} ({user['name']['givenName']} {user['name']['familyName']})")
            continue

        try:
            result = admin_service.users().insert(body=user).execute()
            print(f"Created user: {result['primaryEmail']}")
        except HttpError as e:
            if e.resp.status == 409:
                print(f"User '{user['primaryEmail']}' already exists. Skipping.")
            else:
                print(f"Error creating user '{user['primaryEmail']}': {e}", file=sys.stderr)
                failures.append(user["primaryEmail"])

    if failures:
        print(f"Failed to create {len(failures)} user(s): {', '.join(failures)}", file=sys.stderr)
        sys.exit(1)


# --- Main ---

def main():
    parser = argparse.ArgumentParser(
        description="Google Workspace Domain Provisioner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-users
    sp_list = subparsers.add_parser("list-users", help="List all users on a domain")
    sp_list.add_argument("domain", help="Domain name")

    # setup-domain
    sp_setup = subparsers.add_parser("setup-domain", help="Add domain to Workspace + configure DNS + verify")
    sp_setup.add_argument("domain", help="Domain name (e.g. example.com)")
    sp_setup.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    # create-users
    sp_users = subparsers.add_parser("create-users", help="Create users on a verified domain")
    sp_users.add_argument("domain", help="Domain name")
    sp_users.add_argument(
        "users",
        nargs="+",
        help='User specs: "FirstName LastName username" (e.g. "John Doe john" creates john@domain)',
    )
    sp_users.add_argument("--password", default=None, help="Default password (prompted if not set)")
    sp_users.add_argument("--no-change-password", dest="change_password", action="store_false", default=True, help="Don't force password change on first login")
    sp_users.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    # provision (full flow)
    sp_prov = subparsers.add_parser("provision", help="Full flow: setup domain + create users")
    sp_prov.add_argument("domain", help="Domain name")
    sp_prov.add_argument("users", nargs="+", help='User specs: "FirstName LastName username"')
    sp_prov.add_argument("--password", default=None, help="Default password (prompted if not set)")
    sp_prov.add_argument("--no-change-password", dest="change_password", action="store_false", default=True, help="Don't force password change on first login")
    sp_prov.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")

    args = parser.parse_args()
    dry_run = getattr(args, "dry_run", False)
    load_env_file()
    config = load_config(dry_run=dry_run)

    if args.command == "list-users":
        list_users(config, args.domain)
    elif args.command == "setup-domain":
        setup_domain(config, args.domain, dry_run=dry_run)
    elif args.command == "create-users":
        password = args.password or ("dry-run" if dry_run else prompt_password())
        create_users(config, args.domain, args.users, password, args.change_password, dry_run=dry_run)
    elif args.command == "provision":
        password = args.password or ("dry-run" if dry_run else prompt_password())
        admin, _ = setup_domain(config, args.domain, dry_run=dry_run)
        create_users(config, args.domain, args.users, password, args.change_password, admin_service=admin, dry_run=dry_run)


if __name__ == "__main__":
    main()
