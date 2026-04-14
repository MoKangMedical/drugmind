# Blatant-Why Integration Notes

This repository does not vendor `blatant-why` directly. Instead, DrugMind extracts the reusable architectural patterns from the real upstream repository and adapts them into native DrugMind runtime components.

## What Was Reused

From the upstream repository at `https://github.com/001TMF/blatant-why`:

- `templates/CLAUDE.md`
  - canonical multi-agent flow: `research -> plan -> design -> screen -> rank`
- `templates/.claude/agents/*.md`
  - specialized agent contracts for research, campaign planning, design, screening, review
- `src/proteus_cli/campaign/state.py`
  - durable campaign state machine and round-based execution
- `src/proteus_cli/campaign/decisions.py`
  - append-only decision audit trail
- `src/proteus_cli/campaign/funnel.py`
  - attrition modeling across the screening funnel
- `src/proteus_cli/scoring/ipsae.py`
  - structure-aware ranking emphasis
- `src/proteus_cli/screening/pareto.py`
  - Pareto-front style multi-objective ranking

## DrugMind Adaptation

The adaptation lives in:

- `/Users/apple/Desktop/DrugMind/integrations/blatant_why_adapter.py`
- `/Users/apple/Desktop/DrugMind/integrations/biologics_pipeline.py`
- `/Users/apple/Desktop/DrugMind/integrations/mcp_bridge.py`
- `/Users/apple/Desktop/DrugMind/integrations/screening_bridge.py`
- `/Users/apple/Desktop/DrugMind/integrations/tamarind_client.py`

### Runtime Mapping

- BY Claude runtime -> DrugMind `DigitalTwinEngine` + MIMO
- BY campaign state -> DrugMind `DrugDiscoveryImplementationHub` + `WorkflowOrchestrator`
- BY knowledge/campaign MCP -> DrugMind `ProjectMemoryStore` + execution history
- BY research MCP servers -> `BlatantWhyMCPBridge`
- BY screening/ranking -> `ScreeningBridge`
- BY Tamarind compute planning -> `TamarindClient`
- BY external collaboration surface -> DrugMind `SecondMeIntegration`

### Capability Mapping

Added DrugMind capabilities:

- `capability.structural_research`
- `capability.dmta_screening_ranking`
- `capability.biologics_design_campaign`
- `capability.campaign_memory`

### Workflow Mapping

Added workflow templates:

- `workflow.discovery_bootstrap`
- `workflow.hit_triage`
- `workflow.candidate_nomination`
- `workflow.biologics_campaign`

## SecondMe Integration

Capability executions can now produce persona-ready sync payloads via:

- `capability.second_me_program_sync`
- `capability.campaign_memory`

And MCP now exposes:

- `drugmind_capabilities`
- `drugmind_execute_capability`
- `drugmind_biologics_campaign`

These are additive to the original 5 DrugMind tools.
