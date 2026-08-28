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
