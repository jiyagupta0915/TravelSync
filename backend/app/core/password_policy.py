"""
The single password policy for NEW passwords (signup, change, reset).

  * 8 to 72 bytes (bcrypt silently ignores anything after 72 bytes, so we refuse longer input)
  * at least one uppercase letter A-Z, one lowercase letter a-z, one digit 0-9
  * at least one special character: anything that is not an ASCII letter, digit or whitespace

The frontend mirrors this exactly in src/utils/passwordPolicy.js. Existing users are NOT
checked against this policy when they log in.
"""

import re

MIN_LENGTH = 8
MAX_BYTES = 72

_UPPER = re.compile(r"[A-Z]")
_LOWER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"[0-9]")
_SPECIAL = re.compile(r"[^A-Za-z0-9\s]")


def password_problems(password: str) -> list[str]:
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"at least {MIN_LENGTH} characters")
    if len(password.encode("utf-8")) > MAX_BYTES:
        problems.append(f"no more than {MAX_BYTES} bytes")
    if not _UPPER.search(password):
        problems.append("an uppercase letter")
    if not _LOWER.search(password):
        problems.append("a lowercase letter")
    if not _DIGIT.search(password):
        problems.append("a number")
    if not _SPECIAL.search(password):
        problems.append("a special character")
    return problems


def validate_new_password(password: str) -> str:
    problems = password_problems(password)
    if problems:
        raise ValueError("Password must contain " + ", ".join(problems) + ".")
    return password
