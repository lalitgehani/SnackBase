# SnackBase Security Test Suite

This suite encodes the findings of the grey-box VAPT of 2026-08-09
(`VAPT_REPORT_2026-08-09.md`) as executable regression guards. Every
Critical/High/Medium finding maps to at least one test ID here.

## Running the suite

```bash
uv run python cleanup_dev.py -y      # always reset dev state first
uv run pytest -m security -v         # the security suite only
uv run pytest -m "not security"      # everything except the security suite
```

A consolidated HTML report is written at the end of every security session by
`tests/security/reporter/html_reporter.py`; the path is printed to stdout.

## The `security` marker

The marker is registered in `pyproject.toml` and applied **automatically** to
every test collected from `tests/security/` by `pytest_collection_modifyitems`
in `tests/security/conftest.py`. New modules do not need a `pytestmark` line —
dropping a file into this tree is enough to have it selected by `-m security`.

## `xfail(strict=True)` convention

Many findings' code fixes are not yet merged. A test that asserts the *secure*
outcome would therefore fail today. Such tests are written against the target
(secure) behaviour and marked:

```python
@pytest.mark.xfail(reason="C-01 fix pending", strict=True)
```

`strict=True` means the test **fails the build if it unexpectedly passes**. When
the corresponding fix lands, the marker must be removed in the same change and
the test becomes a permanent regression guard. Always tag the reason with the
finding ID so `grep "C-01"` finds both the test and its tracking note.

## Test ID groups

Test names carry an ID prefix so a finding can be traced to its guard by grep.

| ID group     | Directory                        | Surface                                   | Findings covered |
| ------------ | -------------------------------- | ----------------------------------------- | ---------------- |
| `AUTH-AZ-*`  | `test_auth/`                     | Authorization bypass                      | —                |
| `AUTH-LI-*`  | `test_auth/`                     | Login security, user enumeration          | M-07             |
| `AUTH-PW-*`  | `test_auth/`                     | Password handling                         | —                |
| `AUTH-TK-*`  | `test_auth/`                     | Token management                          | —                |
| `AUTH-RF-*`  | `test_auth/`                     | Refresh-token reuse detection             | M-05             |
| `AUTH-INV-*` | `test_auth/`                     | Invitation-token storage                  | M-06             |
| `RATE-*`     | `test_auth/`                     | Login brute-force / rate limiting         | H-02             |
| `SAML-*`     | `test_auth/`                     | SAML assertion validation                 | H-03             |
| `ISO-AC-*`   | `test_isolation/`                | Record-router account isolation           | —                |
| `ISO-ANON-*` | `test_isolation/`                | Anonymous `X-Account-ID` tenant targeting | M-08             |
| `FILE-TRV-*` | `test_files/`                    | File path traversal                       | C-01             |
| `FILE-MIME-*`| `test_files/`                    | Upload MIME content sniffing              | M-02             |
| `FILE-SIZE-*`| `test_files/`                    | Upload size limits / memory DoS           | M-03             |
| `FILE-AUTHZ-*`| `test_files/`                   | Per-record download authorization         | M-04             |
| `EP-SQLI-*`  | `test_endpoints/`                | Custom-endpoint aggregate SQL injection   | C-02             |
| `EP-ISO-*`   | `test_endpoints/`                | Custom-endpoint cross-tenant isolation    | —                |
| `FN-SBX-*`   | `test_functions/`                | Functions sandbox isolation               | C-04             |
| `FN-ISO-*`   | `test_functions/`                | Functions cross-tenant isolation          | —                |
| `RT-*`       | `test_realtime/`                 | Realtime authorization & payload filtering| M-01             |
| `SSRF-WH-*`  | `test_ssrf/`                     | Webhook SSRF URL validation               | H-01             |
| `CFG-KEY-*`  | `test_config/`                   | Signing-key production validation         | C-03             |
| `CFG-BUILD-*`| `test_config/`                   | Build/runtime config invariants           | M-09             |
| `CFG-LOG-*`  | `test_config/`                   | Production logging bootstrap              | M-10             |
| `DEP-*`      | `test_config/`                   | Dependency version pins                   | H-04             |

## Shared fixtures and helpers

`tests/security/conftest.py` provides the two-tenant harness:

| Fixture                | Yields                                                             |
| ---------------------- | ------------------------------------------------------------------ |
| `security_test_data`   | Accounts A/B, users, and tokens (`user_a_token` admin, `user_b_token` low-privilege, `admin_b_token` admin) |
| `two_tenant_files`     | One uploaded file per account (`account_a_path`, `account_b_path`)  |
| `two_tenant_collection`| One shared public collection with one record per account            |
| `two_tenant_endpoints` | One custom endpoint per account plus its dispatcher URL             |
| `two_tenant_functions` | One function per account (skips if functions are unavailable)       |
| `attack_client`        | HTTP client that logs every request into the HTML report            |

`tests/security/helpers/` provides:

- `assert_denied(response, allowed=(401, 403, 404), leak_markers=())`
- `assert_no_leak(response, *markers)`
- `assert_allowed(response, allowed=(200, 201))`
- `cross_tenant_matrix(attack_client, victim_url=..., victim_token=..., attacker_token=..., write_body=None)`
