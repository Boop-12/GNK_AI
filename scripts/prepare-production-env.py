"""Run once on the Oracle VM. Never display or overwrite deployment secrets."""
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / ".env"


def read_values(path):
    values = {}
    if path.is_file():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("\"").strip("'")
    return values


if __name__ == "__main__":
    if os.name != "posix":
        raise SystemExit("Run on the Oracle VM only.")
    values = read_values(ROOT / ".env.example")
    values["JWT_SECRET_KEY"] = secrets.token_hex(32)
    values["POSTGRES_PASSWORD"] = secrets.token_hex(32)
    values["DATABASE_URL"] = f"postgresql+psycopg://app:{values['POSTGRES_PASSWORD']}@postgres:5432/gnkalgo"
    # Reuse mail delivery settings on this VM without copying broker or AI secrets.
    existing = read_values(Path("/opt/gnkalgo-release/.env"))
    for key in ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM"):
        if existing.get(key):
            values[key] = existing[key]
    descriptor = os.open(TARGET, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as output:
        output.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")
    print("Private production .env created. Live execution and AI provider calls remain disabled.")
    print("SMTP configuration present:", bool(values.get("SMTP_HOST") and values.get("SMTP_FROM")))
