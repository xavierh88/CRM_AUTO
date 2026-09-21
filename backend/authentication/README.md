# Authentication foundation

Status: **local runtime integration implemented and tested with synthetic persistence;
production readiness remains PARTIAL**. `foundation.py` still performs no I/O.
`runtime.py` is now shared by `server.py` and `auth.py`. The runtime uses the
existing MongoDB handle, without loading configuration itself. Tests extract real
HTTP handlers into an isolated FastAPI app; they never import configured startup.
WebAuthn remains **PENDING_EXTERNAL**. No biometric data is inspected or stored.

## Runtime session boundary

The existing `/api/auth/login` email/username-in-`email` and password contract is
preserved. Successful login creates a random session, persists its SHA-256 ID,
and returns the existing `{token, user}` shape with allowlisted user fields.
JWTs require expiration, user ID and session ID; embedded role claims grant
nothing. Each authenticated request checks persisted session expiry/revocation
and reloads enabled account status and role. Legacy JWTs without session IDs
fail closed and require a new password login. The unused stateless token helper
functions were removed to avoid minting tokens that bypass this boundary.

`POST /api/auth/logout` revokes that session. `POST /api/auth/reauthenticate`
accepts a password and records the server time only after verification. It does
not approve an action, issue a confirmation ticket, or prove human presence.
`GET /api/auth/passkeys/options` returns unavailable/PENDING_EXTERNAL; there is no
assertion or enrollment endpoint. Registration remains inactive/telemarketer and
cannot accept a caller-supplied role. Invalid bcrypt input produces HTTP 422.

Collections: `auth_sessions` records creation, expiry, revocation and latest
password reauthentication; `auth_events` records credential/account denials;
`auth_attempts` uses atomic Mongo `$inc` with `_id` uniqueness for a limit of ten
attempts per identifier per five-minute fixed window, including reauthentication.
Attempt keys are HMACs and do not store submitted identifiers. Sessions never
store raw bearer tokens. A persistence failure does not issue a successful login.
These are auditable state boundaries, not a complete append-only audit system.

Persistence was tested with a synthetic collection double, not a running MongoDB.
Real multiworker atomicity, retention/TTL indexes, database failure recovery,
source-wide throttling, event-loop load and full configured startup remain
unverified. Per-account limiting alone does not prevent attacks across many
identifiers; bcrypt remains synchronous as in the original runtime. No indexes,
real databases, services or credentials were accessed or changed for this task.

## Safe password fallback

`hash_password` and `verify_password` use the existing bcrypt format. They reject
empty, malformed Unicode and over-72-byte passwords instead of truncating them.
Verification rejects malformed hashes and unreasonable work factors (supported
cost range 4–14); new hashes use cost 12. Existing higher-cost hashes require an
explicit migration decision, not a silent reset. Passwords are not normalized.
These helpers alone are not a complete login or recovery service.

The host must authenticate against the persisted password hash, reload account
status and role, enforce distributed account/source throttling, use a dummy hash
for unknown accounts, and return generic credential failures. Use the same
account restrictions for passwords and passkeys. Enrollment needs a password
strength policy, locally available compromised-password checks, and an audited
migration plan. Never create a fallback password automatically after a failed or
cancelled passkey ceremony. Recovery and password changes require independently
verified identity, session revocation and audit; email/SMS recovery is pending.
Never log submitted passwords, hashes, session tokens or WebAuthn responses.

## WebAuthn architecture contract

Before enabling passkeys, integrate a reviewed WebAuthn verification library;
do not implement signature/CBOR verification here. Required host behavior:

1. Generate unpredictable challenges on the server, with a short expiry and
   atomic single-use consumption. Bind each to ceremony type, session, tenant,
   account where known, RP ID and exact configured allowed origin. Reject
   cross-origin ceremonies unless explicitly designed and reviewed.
2. Registration requires an active authenticated account, recent password or
   passkey reauthentication, and explicit human approval. Require user
   verification; request no attestation unless separately justified.
3. Verify challenge, type, origin, RP ID hash, user presence, user verification,
   signature and supported algorithms using the library. For authentication,
   resolve credential ownership server-side; validate the user handle against
   that owner, never a supplied user ID. Enforce credential ID uniqueness.
4. Store only account/tenant ownership, opaque credential ID and user handle,
   public key, counter, backup metadata, creation/last-used/revocation timestamps
   and a bounded user label. Do not retain raw attestation/assertion payloads.
   Fingerprints, face images, templates and private keys stay on the device.
5. Treat signature counters with the library's backup-aware policy: synced
   passkeys may use zero/non-monotonic counters. Suspicious changes require
   policy evaluation; do not silently weaken verification.
6. Recheck enabled account and current permissions before issuing a rotated
   session. Require explicit selection of password fallback after cancellation,
   unsupported hardware or verification failure. None is successful login.
7. Removing a passkey requires recent reauthentication, confirmation, ownership
   and at least one remaining independently verified authentication method.
   Revoke affected sessions and append audit events in the same transaction.

## Permissions and confirmation boundary

`Actor` is trusted host input, never a request-body or LLM-deserialized object.
The host constructs it from a verified session and fresh server-side account
state, including tenant, human origin and successful reauthentication time.
A boolean or timestamp supplied by a browser is not authentication evidence.

`ConfirmationGate` supports admin user management, SYSTEM_DEVELOPER schema edits,
and own-account passkey management. Admin does not imply developer access.
Unknown actions and all external actions are denied. Existing CRM object-level
policy remains required; this gate grants no record access or role assignment.

The host first authorizes the target and produces a canonical immutable action
payload and SHA-256 digest. It presents that exact preview to the human and
stores the payload server-side. Only an explicit human confirmation handler may
call `confirm`; AI tools cannot approve their own work. Confirmation rechecks
actor permissions, session binding, five-minute reauthentication and preview
expiry, target and payload digest. A successful ticket can be consumed once,
including concurrent calls. Session revocation or role changes must be reflected
in the fresh Actor supplied at confirmation.

The gate executes nothing. Its memory is process-local, bounded and cleared on
restart; it is unsuitable for multiworker enforcement. Production integration
needs shared atomic ticket consumption, account/session revocation checks,
optimistic version checks on the target, action application and durable audit
in one transaction. A failed transaction requires a fresh preview; never replay
an approved ticket. Audit actor/action/target/result and relevant versions,
without authentication secrets. Denied actions should also be audited by host.

## Verification and pending integration

Run `python3 -m pytest tests/authentication -q` and
`python3 -m compileall -q backend/authentication tests/authentication`.

Remaining work: reviewed WebAuthn library, persistent challenges and credentials,
reauthentication session rotation, login UI/browser ceremony tests, recovery,
append-only audit, retention, source throttling, live persistence validation and
transactional confirmation wiring. Current CRM roles deliberately still exclude
SYSTEM_DEVELOPER; no new developer route or privilege was introduced.
External services remain MOCK/PENDING_EXTERNAL. No deployment is authorized.
