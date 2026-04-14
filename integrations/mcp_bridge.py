"""
Bridge BY-style research MCP servers into DrugMind capability planning.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from datetime import datetime
from typing import Any

from .structure_clients import RcsbPdbClient, SabdabClient, UniProtClient


@dataclass
class MCPServerSpec:
    """Description of a reusable MCP server from BY."""

    server_id: str
    name: str
    domain: str
    description: str
    tools: list[str] = field(default_factory=list)
    reusable_in_drugmind: bool = True
    notes: list[str] = field(default_factory=list)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class BlatantWhyMCPBridge:
    """Catalog and live bridge for BY-style structural biology providers."""

    def __init__(
        self,
        *,
        uniprot_client: UniProtClient | None = None,
        pdb_client: RcsbPdbClient | None = None,
        sabdab_client: SabdabClient | None = None,
    ):
        self.uniprot_client = uniprot_client or UniProtClient()
        self.pdb_client = pdb_client or RcsbPdbClient()
        self.sabdab_client = sabdab_client or SabdabClient()
        self.servers = [
            MCPServerSpec(
                server_id="by-pdb",
                name="PDB",
                domain="structural_biology",
                description="Protein Data Bank structure search and structure context.",
                tools=["pdb_search", "pdb_get_structure", "pdb_ligand_context"],
                notes=["Use for target structure coverage, co-complexes, and template quality."],
            ),
            MCPServerSpec(
                server_id="by-uniprot",
                name="UniProt",
                domain="target_biology",
                description="Canonical target sequence, isoforms, domains, and annotations.",
                tools=["uniprot_lookup", "uniprot_domains", "uniprot_disease"],
                notes=["Use before any design or assay planning work."],
            ),
            MCPServerSpec(
                server_id="by-sabdab",
                name="SAbDab",
                domain="biologics_prior_art",
                description="Existing antibody/nanobody complexes, affinities, and epitope priors.",
                tools=["sabdab_pdb_summary", "sabdab_affinity_summary", "sabdab_epitope_lookup"],
                notes=["Useful for biologics epitope competition and prior-art review."],
            ),
            MCPServerSpec(
                server_id="by-campaign",
                name="Campaign State",
                domain="campaign_management",
                description="Campaign state, transitions, rounds, and design-screen-rank checkpoints.",
                tools=["campaign_get_state", "campaign_update_state", "campaign_log_round"],
                notes=["Adapted into DrugMind implementation and workflow state."],
            ),
            MCPServerSpec(
                server_id="by-knowledge",
                name="Knowledge",
                domain="learning_system",
                description="Cross-campaign knowledge base, scaffold performance, and lessons learned.",
                tools=["knowledge_search", "knowledge_store_campaign", "knowledge_store_failure"],
                notes=["Adapted into project memory plus capability execution history."],
            ),
        ]

    def describe(self) -> dict[str, Any]:
        return {
            "servers": [asdict(server) for server in self.servers],
            "recommended_for_reuse": [
                server["server_id"]
                for server in [asdict(item) for item in self.servers]
                if server["reusable_in_drugmind"]
            ],
            "live_providers": {
                "uniprot": self.uniprot_client.describe(),
                "pdb": self.pdb_client.describe(),
                "sabdab": self.sabdab_client.describe(),
            },
        }

    def list_servers(self, domain: str = "") -> list[dict[str, Any]]:
        servers = [asdict(server) for server in self.servers]
        if domain:
            servers = [server for server in servers if server["domain"] == domain]
        return servers

    def build_target_research_plan(
        self,
        *,
        target: str,
        modality: str,
        disease: str = "",
    ) -> dict[str, Any]:
        queries = [
            {
                "server_id": "by-uniprot",
                "tool": "uniprot_lookup",
                "objective": f"Confirm canonical sequence and domains for {target}.",
            },
            {
                "server_id": "by-pdb",
                "tool": "pdb_search",
                "objective": f"Find the best structure or co-complex for {target}.",
            },
        ]
        if modality in {"biologics", "protein", "antibody", "nanobody"}:
            queries.append(
                {
                    "server_id": "by-sabdab",
                    "tool": "sabdab_pdb_summary",
                    "objective": f"Check whether top {target} structures appear in SAbDab and summarize antibody prior art.",
                }
            )
        queries.append(
            {
                "server_id": "by-knowledge",
                "tool": "knowledge_search",
                "objective": f"Find prior DrugMind or BY-like campaigns related to {target} / {disease}.",
            }
        )
        return {
            "target": target,
            "modality": modality,
            "disease": disease,
            "queries": queries,
            "expected_outputs": [
                "target dossier",
                "best structure recommendation",
                "prior-art / epitope summary",
                "campaign constraints",
            ],
        }

    def run_target_research(
        self,
        *,
        target: str,
        modality: str,
        disease: str = "",
        organism_id: int = 9606,
        organism_label: str = "human",
        pdb_rows: int = 6,
        sabdab_limit: int = 6,
    ) -> dict[str, Any]:
        plan = self.build_target_research_plan(target=target, modality=modality, disease=disease)
        uniprot_search = self.uniprot_client.search_target(target, organism_id=organism_id, size=5)
        primary_uniprot = uniprot_search.get("results", [{}])[0] if uniprot_search.get("results") else {}
        accession = primary_uniprot.get("primary_accession", "")
        uniprot_entry = self.uniprot_client.get_entry(accession) if accession else {}
        pdb_search = self.pdb_client.search_target(
            target,
            organism=organism_label,
            accession=accession,
            rows=pdb_rows,
        )
        pdb_ids = [item.get("pdb_id", "") for item in pdb_search.get("structures", []) if item.get("pdb_id")]
        sabdab_hits = self.sabdab_client.lookup_many(pdb_ids, limit=sabdab_limit) if modality in {"biologics", "protein", "antibody", "nanobody"} else []
        top_structure = pdb_search.get("structures", [{}])[0] if pdb_search.get("structures") else {}

        evidence_summary = self._build_evidence_summary(
            target=target,
            uniprot_entry=uniprot_entry,
            pdb_search=pdb_search,
            sabdab_hits=sabdab_hits,
        )
        return {
            "target": target,
            "modality": modality,
            "disease": disease,
            "research_plan": plan,
            "uniprot": {
                "search": uniprot_search,
                "primary_entry": uniprot_entry,
            },
            "pdb": pdb_search,
            "sabdab": {
                "hits": sabdab_hits,
                "count": len(sabdab_hits),
            },
            "top_recommendation": {
                "uniprot_accession": accession,
                "top_structure": top_structure,
                "sabdab_hit_count": len(sabdab_hits),
            },
            "evidence_summary": evidence_summary,
        }

    def build_campaign_state_contract(self, *, modality: str) -> dict[str, Any]:
        states = [
            "draft",
            "configured",
            "planned",
            "designing",
            "screening",
            "ranked",
            "candidate_review",
            "synced_to_second_me",
        ]
        if modality in {"biologics", "protein"}:
            states.insert(4, "refolding_validation")
        return {
            "modality": modality,
            "states": states,
            "tracked_fields": [
                "project_id",
                "campaign_id",
                "phase",
                "design_batch_id",
                "top_candidates",
                "decision_log_ids",
                "second_me_binding_ids",
            ],
        }

    def _build_evidence_summary(
        self,
        *,
        target: str,
        uniprot_entry: dict[str, Any],
        pdb_search: dict[str, Any],
        sabdab_hits: list[dict[str, Any]],
    ) -> dict[str, Any]:
        structures = pdb_search.get("structures", [])
        return {
            "headline": (
                f"{target} research bundle: UniProt={uniprot_entry.get('primary_accession', 'N/A')}, "
                f"PDB structures={len(structures)}, SAbDab antibody entries={len(sabdab_hits)}"
            ),
            "functions": uniprot_entry.get("function", [])[:3],
            "disease_links": uniprot_entry.get("disease", [])[:3],
            "top_structure_titles": [item.get("title", "") for item in structures[:3]],
            "sabdab_antigens": sorted(
                {
                    antigen
                    for hit in sabdab_hits
                    for antigen in hit.get("antigen_names", [])
                }
            )[:6],
        }
