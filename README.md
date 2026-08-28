# org-threat-profile

A Claude Code skill that builds a cited organizational profile and
evidence-linked risk indicators for a named organization, using two
subagents:

- **org-collector** — gathers publicly available information across five
  layers (business/operational, technology, infrastructure, AI/ML,
  security) into a cited, stated/inferred-marked YAML profile.
- **org-analyst** — turns that profile into evidence-linked risk
  indicators (JSON), without collecting any new facts.

## Use case

Defensive use only: an organization assessing its own public attack
surface, or a documented third-party/vendor risk review. Not intended for
offensive reconnaissance or attack planning.

## Install

Copy `.claude/agents/org-collector.md`, `.claude/agents/org-analyst.md`,
and `.claude/skills/org-threat-profile/SKILL.md` into the equivalent paths
of a Claude Code project, then invoke the skill with an organization name
and domain.

## Output

- `<domain>_profile.yaml` — the cited organizational profile
- `<domain>_risk_indicators.json` — evidence-linked risk indicators, each
  tagged with category, evidence basis (stated/inferred/absence), source
  fields, citations, and caveats

The analyst produces flagged observations only — no severity scoring,
ranking, or remediation advice. That judgment is left to whoever consumes
the output.

## How the two agents work

### org-collector

Tools: `WebSearch`, `WebFetch`. This agent does open-ended research, so it
needs a stopping rule or it could search indefinitely. It tracks budget and
coverage **per layer** (business_operations, technologies, infrastructure,
ai_ml, security — security covers five YAML sections: identity_and_access,
compliance, security_controls, supply_chain, incidents). For each layer it
stops as soon as any one of these is true:

1. **Hard budget** — 6 `WebSearch` calls or 20 `WebFetch` calls spent on
   that layer (a safety ceiling, not a target).
2. **Coverage met** — every field the layer owns is either citable and
   populated, or genuinely attempted and honestly marked `unknown`.
3. **High-priority sources exhausted** — it has worked through the layer's
   listed source types (trust center, docs, GitHub org, careers page,
   etc.) before resorting to secondary/community sources.

There is no early "diminishing returns" exit — a layer keeps going until
it hits the hard budget, is fully covered, or exhausts its high-priority
source list, so it won't bail out of a layer just because a few fetches in
a row came up empty.

Conditions 2 and 3 are checked against a fixed **coverage checklist** —
for each layer, the exact fields it owns and the source types to try for
them:

| Layer | Fields it owns | Source types to try |
|---|---|---|
| `business_operations` | industry, products, notable_customers, headcount, funding_financials, locations, org_structure, leadership, hiring_signals, partnerships | homepage/about page, investor relations or public filings, press/news coverage, Wikipedia, careers page, leadership/about page |
| `technologies` | cloud_providers, languages_frameworks, databases, security_tools | engineering blog, developer/API docs, changelogs, GitHub org/repos, job postings |
| `infrastructure` | hosting_model, architecture_patterns, cdn_and_edge, regions_or_geography, data_residency | engineering blog (architecture posts), docs, trust center, status page |
| `ai_ml` | ai_features, model_providers, inference_hosting, ai_governance, ai_supply_chain | product/pricing pages, AI or responsible-AI pages, model cards, integration pages, engineering blog |
| `security` (one layer, five YAML sections: identity_and_access, compliance, security_controls, supply_chain, incidents) | auth_methods, sso_support, mfa, certifications, regulated_data_types, network, data_protection, testing_and_assurance, subprocessors, notable_dependencies, incidents[] | trust center, security/compliance pages, legal/DPA/subprocessor pages, KB/help-center SSO or MFA docs, incident disclosures, third-party incident writeups, security-vendor or news coverage of incidents |

A layer counts as covered (condition 2) only once *every* field in its row
has either a citable value or a genuine attempt against its listed source
types came up empty — checking just one source type before giving up on a
field doesn't count. "High-priority sources exhausted" (condition 4) means
the layer's listed source types have been worked through, not that every
possible page of that type has been read.

Every populated value is marked `(stated)` (a fetched source explicitly
asserts it) or `(inferred)` (derived via conservative, industry-standard
inference, never invented) and carries `[Sx]` citation tags resolved in a
trailing "Source key" block. It never draws risk conclusions itself — that
is left entirely to the analyst — and it only profiles the organization,
never enriches named individuals beyond a public role+name.

### org-analyst

Tools: none (only `Read`, unused in practice — it exists only in case the
profile arrives as a file path instead of inline text). This agent has no
web access; it reasons only over the profile text it's given in the
prompt, in a single pass — there's no search loop, so it needs no budget
or stopping criteria the way the collector does.

It scans the profile through **7 fixed risk lenses** (its `category`
enum): `external_attack_surface`, `identity_and_access_exposure`,
`supply_chain_dependency`, `compliance_gap_signal`, `incident_recurrence`,
`ai_supply_chain_exposure`, `data_exposure_signal`, plus a catch-all
`other`. For each lens it looks at the profile fields that lens maps to
and, where it finds material, emits an indicator that does one of three
things:

1. **Direct read** — a single `(stated)` field is itself the risk signal
   (e.g. an incident's attack vector, taken as-is).
2. **Cross-reference** — two fields from different sections are compared
   to surface a gap or tension the profile never states outright (e.g.
   comparing `compliance.certifications` against `incidents[]` to note
   that certification didn't prevent the disclosed incident).
3. **Structural inference** — breadth or architecture implies exposure
   (e.g. many identity providers or subprocessors implying a wider attack
   surface), always tagged `inferred_evidence` with a caveat that scale
   alone isn't proof of a weakness.

Every indicator must trace to specific `basis_fields` and `[Sx]` citations
already in the input profile — no new facts, no exploitability claims, no
attacker attribution, no invented attack chains, no CVE unless the profile
itself cited one. If a lens has no supporting material in the profile, it
is simply omitted rather than forced — an empty result is valid. Final
output is strict JSON only, no prose.
