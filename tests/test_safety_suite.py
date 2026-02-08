from pathlib import Path
import sys
import types

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

sys.modules.setdefault("httpx", types.SimpleNamespace(Client=None))

from eval.safety_suite import has_pii_leakage


def test_pii_leak_detects_unmasked_email_and_card():
    assert has_pii_leakage("email alice@example.com")
    assert has_pii_leakage("card 4242424242424242")


def test_pii_leak_allows_masked_email():
    assert not has_pii_leakage("contact al***@example.com")
