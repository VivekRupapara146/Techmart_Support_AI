"""
One-time helper: hash a chosen demo password for DEMO_PASSWORD_HASH.

Run: python -m scripts.generate_password_hash
"""
import getpass
import bcrypt


def main() -> None:
    password = getpass.getpass("Choose a demo password (input hidden): ")
    confirm = getpass.getpass("Confirm: ")
    if password != confirm:
        print("Passwords didn't match. Try again.")
        return

    hashed = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
    print("\nAdd this to your .env (or Render env vars) as DEMO_PASSWORD_HASH:\n")
    print(hashed)
    print("\n(This is a one-way hash — the plaintext password isn't stored anywhere.)")


if __name__ == "__main__":
    main()
