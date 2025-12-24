
import sys
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Any

# Adjust path to find snackbase package
import os
sys.path.append(os.getcwd() + "/src")

from snackbase.core.rules import evaluate_rule, parse_rule

@dataclass
class UserContext:
    id: int
    role: str
    groups: List[str]
    settings: Optional[dict] = None

def run_verification():
    print("Verifying Built-in Macros...")
    
    # 1. @has_group
    user_g = UserContext(id=1, role="user", groups=["admin", "editor"])
    ctx_g = {"user": user_g}
    assert evaluate_rule(parse_rule("@has_group('admin')"), ctx_g) is True
    assert evaluate_rule(parse_rule("@has_group('guest')"), ctx_g) is False
    print("✅ @has_group verified")

    # 2. @has_role
    user_r = UserContext(id=2, role="manager", groups=[])
    ctx_r = {"user": user_r}
    assert evaluate_rule(parse_rule("@has_role('manager')"), ctx_r) is True
    assert evaluate_rule(parse_rule("@has_role('admin')"), ctx_r) is False
    print("✅ @has_role verified")

    # 3. @owns_record
    user_o = UserContext(id=10, role="user", groups=[])
    rec_o = {"owner_id": 10, "title": "My Record"}
    ctx_o = {"user": user_o, "record": rec_o}
    assert evaluate_rule(parse_rule("@owns_record()"), ctx_o) is True
    
    rec_other = {"owner_id": 99}
    ctx_other = {"user": user_o, "record": rec_other}
    assert evaluate_rule(parse_rule("@owns_record()"), ctx_other) is False
    print("✅ @owns_record verified")

    # 4. @in_time_range
    # Using current time, so we pick a wide range covering "now"
    now_hour = datetime.now().hour
    # Range 0-24 should always be true
    assert evaluate_rule(parse_rule("@in_time_range(0, 24)"), {}) is True
    # Range 25-26 should always be false
    assert evaluate_rule(parse_rule("@in_time_range(25, 26)"), {}) is False
    
    print("✅ @in_time_range verified")
    
    # 5. @has_permission
    ctx_p = {
        "permissions": {
            "documents": ["read", "write"]
        }
    }
    assert evaluate_rule(parse_rule("@has_permission('read', 'documents')"), ctx_p) is True
    assert evaluate_rule(parse_rule("@has_permission('delete', 'documents')"), ctx_p) is False
    print("✅ @has_permission verified")

    print("\nAll macros verified successfully!")

if __name__ == "__main__":
    try:
        run_verification()
    except AssertionError as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
