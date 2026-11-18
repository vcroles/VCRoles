# Permission retries

Role/nickname updates and generated-channel cleanup use temporary, scoped
cooldowns for missing permissions and Discord HTTP 403 responses. The delays
are 30 seconds, 1 minute, 2 minutes, 5 minutes, 10 minutes, then 15 minutes.
An expiry permits a single trial when related work next arrives; it does not
start a timer task or replay an old voice event.

## Scope and recovery

- Missing guild-wide Manage Roles or Manage Nicknames permissions share a
  cooldown for that capability in that guild. Recovery checks fetch the bot's
  own membership and current role definitions; they never use a member edit as
  a test of guild-wide access. Unexpected member-edit permission failures stay
  scoped to the member and capability. Nickname failures do not stop role
  updates, and role failures do not stop nickname updates.
  These capabilities are written separately when both are requested. Nickname
  data is refreshed after a role write so a moderator's rename is respected.
- Unassignable roles are omitted using the current role cache. Making a role
  assignable allows it to be used again on the next relevant event.
- Cleanup deletion and channel lookup failures are scoped to the affected
  channel and operation. Database records remain available for recovery.
- A change in cached effective permissions or the bot's role hierarchy allows
  an early trial. Restoring a known missing guild permission also clears that
  capability's cooldown immediately on the next event.
- For guild capability and cleanup checks, a negative permission cache cannot
  permanently block requests. After a cooldown, guild capabilities use the
  read-only self-check, while channel cleanup permits a real deletion trial
  with the usual audit and safety guards. An unchanged negative cache does
  not prevent normal work after successful HTTP verification. Obfuscated
  channel metadata remains subject to the separate visibility safety guards.
- Related events share an in-progress guild self-check. If it confirms recovery,
  those events can proceed without each issuing another self-check.
- An ineligible nickname or failed member fetch/edit cannot determine the
  guild's recovery outcome. A member failure following HTTP verification requests
  an immediate read-only self-check; it imposes a new guild cooldown only if the
  bot's own permission/access check fails. The individual member retains its
  own cooldown. Confirmed guild permission failures continue to back off.

Member operations resume on fresh voice events. Skipped joins/leaves are not
stored for replay: an old join must not add a role after a member has left.
This does not retroactively repair every role missed during an outage.
Cleanup retries run through its existing five-minute reconciliation sweep,
which may make retries less frequent than the nominal cooldown. Normal
occupancy, shard-health, vacancy-grace, and durable audit checks still apply.

Cooldowns and successful permission probes use bounded, in-memory caches with
24-hour expiry. Restarting resets them and allows fresh trials. These caches
hold no pending Discord mutations. Only permission failures trigger this
backoff for member edits and cleanup. Transport failures while rechecking
already-negative guild permissions also back off, with a separate
`permission_probe_unavailable` diagnostic. Discord's library continues to
manage HTTP 429 rate limits.

## Diagnostics

`permission_retry_scheduled` records the reason, scope, failure count, delay,
and the number of suppressed calls since the preceding diagnostic. Suppressed
events increment counters without writing another traceback.
`permission_retry_reset` records a cached permission change;
`permission_retry_recovered` records a successful trial or the removal of a
known cached permission blocker, with suppressed counts.
These use the existing persistent JSON logging and OTLP event export.
Actual deletion attempts retain their durable audit intents and outcomes.

The `vcroles.permission_retry.events` counter has bounded `operation` and
`event` labels (`failed`, `suppressed`, `reset`, `recovered`). Guild/member/channel
identifiers remain in local diagnostic context, not metric labels or exported
event attributes. A known deferral is recorded as `deferred` rather than a
successful member update; an actual failed HTTP trial is still an error.

Example PromQL:

```promql
sum by (operation, event) (rate(vcroles_permission_retry_events_total[15m]))
```

Example LogQL (adjust the service selector to your deployment):

```logql
{service_name="vcroles"} |= "permission_retry_"
```
