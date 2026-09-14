# Documenso — audit notes (2026-09-14)

**Source:** documenso/documenso @ HEAD, package.json 2.18.0. **Outcome:** one real
access-control gap, but HIGH duplicate-overlap with public CVE-2026-85697 →
`nothing_submittable` without a human novelty check.

## The gap (verified in code)
All file/PDF-serving routes authorize via `checkEnvelopeFileAccess`
(`apps/remix/server/api/files/files.helpers.ts`): it calls `getTeamById({userId,teamId})`
and returns true for ANY team member (any role) — it never applies document VISIBILITY.
The canonical document access path (`getMultipleEnvelopeWhereInput`,
`packages/lib/server-only/envelope/get-envelopes-by-ids.ts`) DOES enforce visibility via
`visibility: { in: TEAM_DOCUMENT_VISIBILITY_MAP[team.currentTeamRole] }`.
=> A low-privilege team MEMBER can view/download the PDF bytes of a MANAGER_AND_ABOVE /
ADMIN-visibility document they cannot see in the normal API, via:
- `GET /api/files/envelope/:envelopeId/envelopeItem/:envelopeItemId` (view)
- `.../download/:version?` (download)
- `get-envelope-item-pdf.ts` route
(needs team membership + knowledge of the envelope/item/documentData IDs, which are random cuids).

## Why NOT submitted (duplicate gate)
CVE-2026-85697 (Medium 6.5, affects 2.17.0, "PDF route ignores document visibility",
"read restricted documents WITHIN their team or cross-tenant") already describes this exact
intra-team visibility read. The 2.18 fix addressed the cross-team half (team scoping) but
left the visibility half — an INCOMPLETE FIX that is still live at HEAD. That is potentially
reportable as an incomplete-fix, BUT the CVE text already claims the intra-team impact, so it
is high-risk to be closed as duplicate/known. A human must diff HEAD against the actual
CVE-2026-85697 fix commit + read the advisory to decide novelty before any submission.

## Also checked (guarded)
- `get-documents-by-ids`, `get-document` tRPC: scoped via envelope where-input (visibility enforced).
- `download.ts` API-token path: team-scoped via `buildTeamWhereQuery` (no cross-team), but also visibility-blind (same class as above).
