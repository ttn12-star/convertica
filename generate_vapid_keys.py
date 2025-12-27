#!/usr/bin/env python
"""
Generate VAPID keys for Web Push notifications.
Run this script once to generate keys, then add them to .env file.
"""

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def main() -> None:
    # Generate P-256 key pair (the curve used by VAPID)
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_key = private_key.public_key()

    # Private key in PEM (PKCS8) for pywebpush
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    # Public key for browser Push API: uncompressed EC point, base64url
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    public_b64url = _b64url(public_raw)

    print("=" * 70)
    print("VAPID Keys Generated Successfully!")
    print("=" * 70)
    print()

    # .env-friendly: keep PEM in one line with \n, then unescape in settings
    private_one_line = private_pem.replace("\n", "\\n")
    print("1. Add PRIVATE KEY to .env file (one-line with \\\n):")
    print("-" * 70)
    print(f'VAPID_PRIVATE_KEY="{private_one_line}"')
    print()

    print("2. Add PUBLIC KEY to .env file (base64url for frontend subscribe):")
    print("-" * 70)
    print(f'VAPID_PUBLIC_KEY="{public_b64url}"')
    print()

    print("3. Add claims (contact email) to .env file:")
    print("-" * 70)
    print('VAPID_CLAIMS_SUB="mailto:admin@convertica.net"')
    print()

    print("=" * 70)
    print("Next steps:")
    print("1. Copy values above into your .env")
    print("2. Restart Django")
    print("3. Re-open the site and re-subscribe to push if needed")
    print("=" * 70)


if __name__ == "__main__":
    main()
