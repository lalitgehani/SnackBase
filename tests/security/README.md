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

### How the report reads outcomes

The report's status vocabulary is deliberately not pytest's, because pytest's
"expected failure" is a security suite's headline result:

| Report status | pytest outcome | Meaning |
| ------------- | -------------- | ------- |
| `PASSED`      | passed         | The boundary holds. |
| `VULNERABLE`  | xfailed        | The asserted secure behaviour does **not** hold — a confirmed, unfixed finding. |
| `FIXED`       | xpassed (strict) | The behaviour now holds; the `xfail` marker is stale and must be removed. |
| `FAILED` / `ERROR` | failed / setup error | A real break. |
| `SKIPPED`     | skipped        | Not exercised (e.g. a feature unavailable in the environment). |

Overall status is `FAILED` if anything failed, errored, or carries a stale
marker; `VULNERABLE` if confirmed findings remain; `PASSED` otherwise.

Outcomes reach the report through `pytest_runtest_makereport` in
`tests/security/conftest.py`. Logged HTTP exchanges are evidence, not verdicts —
they are labelled `ALLOWED`/`DENIED` by what the server did, and the pass/fail
meaning comes from the test outcome alone.

## The `security` marker

The marker is registered in `pyproject.toml` and applied **automatically** to
every test collected from `tests/security/` by `pytest_collection_modifyitems`
in `tests/security/conftest.py`. New modules do not need a `pytestmark` line —
dropping a file into this tree is enough to have it selected by `-m security`.

## `xfail(strict=True)` convention

**Every Critical, High and Medium finding is now fixed, so the suite carries no
`xfail` markers at all.** A run should report only `PASSED` and the three
platform-conditional `SKIPPED` guards below; a `VULNERABLE` row means a fix has
regressed.

The convention stays documented because it is how a newly-found issue is
guarded. A test that asserts the *secure* outcome for an unfixed finding would
fail today, so such tests are written against the target (secure) behaviour and
marked:

```python
@pytest.mark.xfail(reason="H-01 fix pending", strict=True)
```

`strict=True` means the test **fails the build if it unexpectedly passes**. When
the corresponding fix lands, the marker must be removed in the same change and
the test becomes a permanent regression guard. Always tag the reason with the
finding ID so `grep "H-01"` finds both the test and its tracking note.

A guard written before its fix can turn out to be unsatisfiable — asserting
something a sibling guard contradicts, or asserting a decision the seam it drives
cannot make. Four did, and each was reshaped when its fix landed, with the reason
recorded in the test docstring and the commit:

| Test | Reshaped because |
| ---- | ---------------- |
| `RT-010/011/012` | Drove a bare `ConnectionManager()` with no rule source while asserting view-rule and projection behaviour. They now build a real collection and use the shipped `RealtimeReadPolicy`, which is the shape F4.1 specified. |
| `FILE-MIME-002` | Asserted the identical upload `FILE-MIME-001` requires to be refused would be accepted — the two halves of F4.2's "rejected **or** neutralized". It now uploads a genuine PNG under an attacker-chosen `.sh` name and asserts the stored extension follows the content. |
| `ISO-ANON-001` | A declared characterisation of pre-fix behaviour, asserting the very request `ISO-ANON-011` requires to be denied. It now opts in and keeps the half that still holds: the tenant scoping is honest. |
| `AUTH-TK-007` | Checked the rotated-in refresh token *after* replaying the spent one, which M-05 turns into family revocation. The two steps are now the other way round. |

## Platform-conditional guards

A few boundaries are enforced by a kernel feature rather than by application
code, so the test can only observe them where that feature exists. Those are
`skipif`, never `xfail` — a skip reports honestly as "not exercised" instead of
claiming a boundary holds on a platform where it does not:

| Guard | Runs where | Mechanism |
| ----- | ---------- | --------- |
| `FN-SBX-001/002` | Linux 5.13+ | Landlock filesystem confinement |
| `FN-SBX-030` | Linux | `setrlimit(RLIMIT_AS)`, which macOS rejects |

They run in CI (`ubuntu-latest`) and in the runtime image, and skip on macOS
development machines. `FN-POL-*` asserts the same policy decisions from the
rules handed to the kernel, so the intent stays covered everywhere.

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
| `FN-BUILD-*` | `test_functions/`                | Functions deploy-time build isolation     | C-04             |
| `FN-POL-*`   | `test_functions/`                | Functions confinement policy              | C-04             |
| `FN-ISO-*`   | `test_functions/`                | Functions cross-tenant isolation          | —                |
| `RT-*`       | `test_realtime/`                 | Realtime authorization & payload filtering| M-01             |
| `SSRF-WH-*`  | `test_ssrf/`                     | Webhook SSRF URL validation               | H-01             |
| `CFG-KEY-*`  | `test_config/`                   | Signing-key production validation         | C-03             |
| `CFG-BUILD-*`| `test_config/`                   | Build/runtime config invariants           | M-09             |
| `CFG-LOG-*`  | `test_config/`                   | Production logging bootstrap              | M-10             |
| `DEP-*`      | `test_config/`                   | Dependency version pins                   | H-04             |

## Finding-to-test map

Every Critical/High/Medium finding from the VAPT of 2026-08-09 is fixed and maps
to at least one test. `grep` the finding ID to reach both the guard and the
remediation note.

| Finding | What it is | Guarded by |
| ------- | ---------- | ---------- |
| C-01 | Cross-tenant file path traversal | `FILE-TRV-001/002/010/011` + the sibling case in `tests/unit/domain/services/test_file_storage_service.py` |
| C-02 | Custom-endpoint aggregate SQL injection | `EP-SQLI-001/004/010` (exploitable), `EP-SQLI-002/003` (already refused) |
| C-03 | Default signing secret accepted in production | `CFG-KEY-001` |
| C-04 | Functions deploy RCE + sandbox | `FN-BUILD-001/002/010/020/021` (deploy), `FN-SBX-001/002/010/030` (invoke), `FN-POL-*` (policy); `FN-SBX-011/020/031` lock in what already worked |
| H-01 | Webhook SSRF | `SSRF-WH-002/003/004/010/011` + `SSRF-WH-012` (IP pinning) |
| H-02 | Login brute force / rate limiting | `RATE-LOGIN-001/002/003/004/005` (per-IP throttle), `RATE-LOGIN-010/011` (per-account lockout), `RATE-LOGIN-012` (trusted-proxy client IP) |
| H-03 | SAML assertion validation | `SAML-ASRT-010/011/012/013` |
| H-04 | Dependency advisory drift | `DEP-001/010/011` + the `dependency-audit` CI job |
| M-01 | Realtime authorization & payload filtering | `RT-010/011/012` (rule, projection, PII) + `RT-013` (delete payload) |
| M-02 | File MIME content sniffing | `FILE-MIME-001/002` + `TestDetectMimeType` in `tests/unit/domain/services/test_file_storage_service.py` |
| M-03 | Upload size limit / memory DoS | `FILE-SIZE-002` |
| M-04 | File download per-record authorization | `FILE-AUTHZ-002` (denied), `FILE-AUTHZ-005` (allowed through a readable record) |
| M-05 | Refresh-token reuse detection | `AUTH-RF-003/004` |
| M-06 | Invitation-token hashing | `AUTH-INV-001` (stored as a hash), `AUTH-INV-002` (issued token still resolves) |
| M-07 | Login user enumeration | `AUTH-LI-010/011/012` |
| M-08 | Anonymous `X-Account-ID` tenant targeting | `ISO-ANON-010/011` + the `allow_anonymous` cases in `tests/integration/test_anonymous_access.py` |
| M-09 | Build/runtime config drift | `CFG-BUILD-010/011` |
| M-10 | Production logging bootstrap | `CFG-LOG-001/002` |

Beyond the one-to-one mapping, `EP-ISO-*` and `FN-ISO-*` extend the record
router's isolation discipline to custom endpoints and functions.

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
