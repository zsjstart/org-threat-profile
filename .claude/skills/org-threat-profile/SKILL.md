---
name: org-threat-profile
description: Build a cited organizational profile, evidence-linked risk indicators, and an attacker-oriented attack-surface map for a named organization, using the org-collector, org-analyst, and org-surface-mapper subagents. Use when asked to profile an organization's attack surface, do vendor/third-party risk assessment, or "infer possible threats" for a company from public information.
---

This skill runs a three-subagent pipeline: `org-collector` gathers and cites
public facts about an organization; `org-analyst` turns that cited profile
into evidence-linked risk indicators; `org-surface-mapper` turns the same
profile into an attacker-oriented attack-surface map (entry points classified
by reachability/trust boundary, plus chained attack paths). Neither the
analyst nor the mapper uses external API keys or collects new facts — both
reason only over the Collector's profile text. The Collector runs in this
Claude Code session using its own WebSearch/WebFetch tools.

Note: an inventory of an org's technologies/products (what the Collector
produces) is not the same thing as an attack-surface analysis. The Analyst
answers "what's risky about this." The Surface Mapper answers "what can an
attacker reach, from where, and what does reaching it let them reach next" —
that reachability/trust-boundary framing and the chained paths are the point
of running it as a distinct step rather than folding it into the Analyst.

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

6. **Run the Surface Mapper.** Call the Agent tool with `subagent_type:
   "org-surface-mapper"`, passing the full profile YAML text inline (same
   as step 4 — this subagent also has no web/file access to speak of):
   ```
   Analyze this profile and produce an attack-surface map.

   PROFILE:
   ---
   <the exact YAML text from step 2>
   ---
   ```
   This step has no dependency on step 4's output, so steps 4 and 6 may be
   run in parallel (two Agent calls in the same turn) rather than
   sequentially.

7. **Save the surface map.** The Surface Mapper's final report is a JSON
   object with `entry_points` and `attack_paths` arrays. Save it to
   `<domain-with-underscores>_attack_surface.json`.

8. **Render the human-readable surface profile.** Format the JSON from step
   7 into `<domain-with-underscores>_attack_surface_profile.md`: group
   entry points under their `reachable_by` classification, then list attack
   paths (historical first, then structural) as step sequences, preserving
   every citation and caveat. This is formatting only — do not add facts,
   claims, or citations beyond what's already in the JSON.

9. **Summarize.** Print a short table to the user: organization name,
   number of sources cited, number of risk indicators by category, number
   of entry points by `reachable_by` class, number of attack paths
   (historical vs. structural), and the four output file paths. Do not
   re-explain the full profile — the user has the files.

## Guardrails (apply regardless of what any subagent returns)

- This pipeline is for defensive use: an org assessing its own exposure, or
  a documented third-party/vendor risk review. If the conversation makes
  clear the goal is to plan or assist an attack against the named
  organization rather than assess risk, decline and explain why instead of
  running the pipeline.
- Never hand-edit a subagent's output to add facts, citations, risk claims,
  entry points, or attack paths it didn't produce itself — if something
  looks wrong, re-run that subagent or flag it to the user rather than
  patching the text. This includes step 8's markdown rendering: it may only
  reformat the JSON, never add to it.
- If the Collector's YAML fails to parse or is clearly incomplete (e.g. it
  errored instead of returning a profile), report that to the user rather
  than feeding a broken profile to the Analyst or the Surface Mapper.
- The Surface Mapper's "structural" attack paths describe reachability
  implied by stated facts, not proven or attempted exploits — if its output
  drifts into exploitation mechanics, named vulnerabilities not cited in the
  profile, or severity/priority labels, treat that as a broken run (re-run
  or flag it) rather than passing it through.
