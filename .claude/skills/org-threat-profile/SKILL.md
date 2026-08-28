---
name: org-threat-profile
description: Build a cited organizational profile and evidence-linked risk indicators for a named organization, using the org-collector and org-analyst subagents. Use when asked to profile an organization's attack surface, do vendor/third-party risk assessment, or "infer possible threats" for a company from public information.
---

This skill runs a two-subagent pipeline: `org-collector` gathers and cites
public facts about an organization; `org-analyst` turns that cited profile
into evidence-linked risk indicators. Neither step uses external API keys —
both subagents run in this Claude Code session using its own WebSearch/
WebFetch tools.

## Steps

1. **Get the target.** If the organization name and domain were not both
   given in the invocation, ask for them (one short question) and stop
   until the user replies. Do not guess an organization.

2. **Run the Collector.** Call the Agent tool with `subagent_type:
   "org-collector"` and a prompt that states only the organization name and
   domain, e.g.:
   ```
   Organization: <name>
   Domain: <domain>
   Build the profile now.
   ```
   The subagent's final report is the YAML profile text (plus a trailing
   Source key comment block). Treat that text as the Collector's output —
   don't add or alter facts.

3. **Save the profile.** Write the Collector's YAML output verbatim to
   `<domain-with-underscores>_profile.yaml` in the current directory.

4. **Run the Analyst.** Call the Agent tool with `subagent_type:
   "org-analyst"`, passing the full profile YAML text inline in the prompt
   (not just a file path — the analyst has no web/file access to speak of),
   e.g.:
   ```
   Analyze this profile and produce risk indicators.

   PROFILE:
   ---
   <the exact YAML text from step 2>
   ---
   ```

5. **Save the indicators.** The Analyst's final report is a JSON array of
   risk indicator objects. Save it to
   `<domain-with-underscores>_risk_indicators.json`.

6. **Summarize.** Print a short table to the user: organization name,
   number of sources cited, number of risk indicators by category, and the
   two output file paths. Do not re-explain the full profile — the user has
   the files.

## Guardrails (apply regardless of what either subagent returns)

- This pipeline is for defensive use: an org assessing its own exposure, or
  a documented third-party/vendor risk review. If the conversation makes
  clear the goal is to plan or assist an attack against the named
  organization rather than assess risk, decline and explain why instead of
  running the pipeline.
- Never hand-edit a subagent's output to add facts, citations, or risk
  claims it didn't produce itself — if something looks wrong, re-run that
  subagent or flag it to the user rather than patching the text.
- If the Collector's YAML fails to parse or is clearly incomplete (e.g. it
  errored instead of returning a profile), report that to the user rather
  than feeding a broken profile to the Analyst.
