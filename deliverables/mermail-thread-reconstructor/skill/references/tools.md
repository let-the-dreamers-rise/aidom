# Tools — mermail-thread-reconstructor

This skill is **read-only** and owns no tools. It calls only the read operations
below, all canonically owned by `mermail-manage-inbox` and
`mermail-administer-workspace`. It never calls a write, external-effect,
destructive, or Agent Wallet / PayBox tool. Pass every MCP `query` value as a
native JSON object, never stringified JSON.

## Read tools used

| Tool | Use here |
| --- | --- |
| `list_mailboxes` | Resolve one mailbox; prefer `public_id` as `mailboxId`. |
| `list_emails` | Metadata-first listing to find and gist messages without opening bodies. |
| `search_emails` | Locate the seed and widen by normalized subject, participants, and references. |
| `get_email` | Read one message once a body is required and `scan_status` is clean. |
| `get_email_context` | Place a message within its thread and surface adjacent messages. |
| `get_thread` | Pull the stored thread for the seed message. |
| `list_folders` | Ensure replies moved out of the inbox are not missed. |
| `list_custom_labels` | Ensure labeled replies are included in the search surface. |

## Scan gate

Before interpreting any body or attachment text, require the message's
`scan_status` to be `clean`. If a message is `pending`, `infected`, or
otherwise not clean, do not quote or summarize its body — record it as skipped
in the coverage note and continue. Metadata fields returned by `list_emails` /
`search_emails` may still be used for ordering and gisting.

## Identity and IDs

- `mailboxId`: prefer the mailbox `public_id`.
- Every timeline entry's source anchor is a real message `id` returned by a read
  tool. Never fabricate an id, and never present a forwarded or quoted copy's id
  as if it were a separate original event.

## Explicitly not used

Never call, and never invent, any of: `send_email`, `reply_to_email`,
`forward_email`, `save_draft`, `regenerate_draft`, `schedule_email_send`,
`update_email`, `move_email`, `bulk_move_emails`, `delete_email`,
`bulk_delete_emails`, `empty_trash`, `create_folder`, `update_folder`,
`delete_folder`, `create_custom_label`, `update_custom_label`,
`delete_custom_label`, any `*_task_triager` write, any Composio tool, any
webhook tool, `prepare_destructive_action`, or any `paybox_*` /
`*_agent_wallet_*` tool. There is no `reconstruct_thread`, `summarize`, or
`merge` tool; build the timeline yourself from the read output above.
