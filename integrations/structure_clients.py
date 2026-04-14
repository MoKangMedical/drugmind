"""
Live structural biology clients used by the BY bridge.
"""

from __future__ import annotations

import csv
import io
from typing import Any

import httpx


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


class UniProtClient:
    """Thin wrapper around the official UniProt REST API."""

    def __init__(self, base_url: str = "https://rest.uniprot.org", timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def describe(self) -> dict[str, Any]:
        return {
            "name": "UniProt REST API",
            "base_url": self.base_url,
            "capabilities": [
                "target_search",
                "entry_lookup",
                "function_and_disease_summary",
            ],
        }

    def search_target(self, target: str, *, organism_id: int = 9606, size: int = 5) -> dict[str, Any]:
        query = f"(gene_exact:{target} OR gene:{target} OR protein_name:{target}) AND organism_id:{organism_id}"
        params = {
            "query": query,
            "format": "json",
            "size": size,
            "fields": ",".join(
                [
                    "accession",
                    "id",
                    "protein_name",
                    "gene_names",
                    "organism_name",
                    "length",
                    "cc_function",
                    "cc_disease",
                    "xref_pdb",
                ]
            ),
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/uniprotkb/search", params=params)
            response.raise_for_status()
            payload = response.json()
        results = [self._summarize_search_hit(item) for item in payload.get("results", [])]
        return {
            "query": query,
            "count": len(results),
            "results": results,
        }

    def get_entry(self, accession: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.base_url}/uniprotkb/{accession}.json")
            response.raise_for_status()
            entry = response.json()
        return self._summarize_entry(entry)

    def _summarize_search_hit(self, item: dict[str, Any]) -> dict[str, Any]:
        protein = item.get("proteinDescription", {})
        recommended = ((protein.get("recommendedName") or {}).get("fullName") or {}).get("value", "")
        genes = []
        for gene in item.get("genes", []):
            gene_name = ((gene.get("geneName") or {}).get("value")) or ""
            if gene_name:
                genes.append(gene_name)
        pdb_refs = [
            ref.get("id")
            for ref in item.get("uniProtKBCrossReferences", [])
            if ref.get("database") == "PDB" and ref.get("id")
        ]
        functions = self._extract_comment_text(item, "FUNCTION")
        diseases = self._extract_comment_text(item, "DISEASE")
        return {
            "primary_accession": item.get("primaryAccession", ""),
            "entry_id": item.get("uniProtkbId", ""),
            "protein_name": recommended,
            "gene_names": genes,
            "organism": ((item.get("organism") or {}).get("scientificName")) or "",
            "length": ((item.get("sequence") or {}).get("length")) or item.get("entryAudit", {}).get("sequenceLength", 0),
            "function": functions[:3],
            "disease": diseases[:3],
            "pdb_references": pdb_refs[:12],
        }

    def _summarize_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        sequence = entry.get("sequence") or {}
        protein = entry.get("proteinDescription", {})
        recommended = ((protein.get("recommendedName") or {}).get("fullName") or {}).get("value", "")
        genes = []
        for gene in entry.get("genes", []):
            gene_name = ((gene.get("geneName") or {}).get("value")) or ""
            if gene_name:
                genes.append(gene_name)
        pdb_refs = [
            ref.get("id")
            for ref in entry.get("uniProtKBCrossReferences", [])
            if ref.get("database") == "PDB" and ref.get("id")
        ]
        return {
            "primary_accession": entry.get("primaryAccession", ""),
            "entry_id": entry.get("uniProtkbId", ""),
            "protein_name": recommended,
            "gene_names": genes,
            "organism": ((entry.get("organism") or {}).get("scientificName")) or "",
            "sequence_length": sequence.get("length", 0),
            "function": self._extract_comment_text(entry, "FUNCTION")[:4],
            "disease": self._extract_comment_text(entry, "DISEASE")[:4],
            "subcellular_location": self._extract_comment_text(entry, "SUBCELLULAR LOCATION")[:4],
            "pdb_references": pdb_refs[:24],
        }

    def _extract_comment_text(self, payload: dict[str, Any], comment_type: str) -> list[str]:
        texts: list[str] = []
        for comment in payload.get("comments", []):
            if comment.get("commentType") != comment_type:
                continue
            for block in _safe_list(comment.get("texts")):
                value = block.get("value") if isinstance(block, dict) else str(block)
                if value:
                    texts.append(value)
            for block in _safe_list(comment.get("disease")):
                if isinstance(block, dict):
                    for value in [block.get("diseaseId"), block.get("description")]:
                        if value:
                            texts.append(str(value))
        return texts


class RcsbPdbClient:
    """Wrapper around the official RCSB Search and Data APIs."""

    SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
    DATA_URL = "https://data.rcsb.org/rest/v1"

    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def describe(self) -> dict[str, Any]:
        return {
            "name": "RCSB PDB Search/Data API",
            "search_url": self.SEARCH_URL,
            "data_url": self.DATA_URL,
            "capabilities": [
                "full_text_search",
                "entry_lookup",
                "polymer_entity_lookup",
            ],
        }

    def search_target(
        self,
        target: str,
        *,
        organism: str = "human",
        accession: str = "",
        rows: int = 6,
    ) -> dict[str, Any]:
        search_term = " ".join(part for part in [target, organism] if part).strip()
        payload = {
            "query": {
                "type": "terminal",
                "service": "full_text",
                "parameters": {"value": search_term},
            },
            "return_type": "entry",
            "request_options": {
                "paginate": {"start": 0, "rows": max(rows * 3, rows)},
            },
        }
        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(self.SEARCH_URL, json=payload)
            response.raise_for_status()
            search = response.json()

        ranked_ids = [item.get("identifier", "") for item in search.get("result_set", []) if item.get("identifier")]
        filtered: list[dict[str, Any]] = []
        fallback: list[dict[str, Any]] = []
        for pdb_id in ranked_ids[: max(rows * 3, rows)]:
            summary = self.get_entry_summary(pdb_id)
            if self._matches_target(summary, target=target, accession=accession):
                filtered.append(summary)
            else:
                fallback.append(summary)
            if len(filtered) >= rows:
                break
        if len(filtered) < rows:
            filtered.extend(fallback[: rows - len(filtered)])

        return {
            "query": search_term,
            "total_count": search.get("total_count", 0),
            "structures": filtered[:rows],
        }

    def get_entry_summary(self, pdb_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.DATA_URL}/core/entry/{pdb_id}")
            response.raise_for_status()
            entry = response.json()

            entity_ids = ((entry.get("rcsb_entry_container_identifiers") or {}).get("polymer_entity_ids")) or []
            polymer_entities = []
            for entity_id in entity_ids[:6]:
                entity_response = client.get(f"{self.DATA_URL}/core/polymer_entity/{pdb_id}/{entity_id}")
                if entity_response.status_code >= 400:
                    continue
                polymer_entities.append(entity_response.json())

        summarized_entities = [self._summarize_polymer_entity(item) for item in polymer_entities]
        return {
            "pdb_id": pdb_id,
            "title": ((entry.get("struct") or {}).get("title")) or "",
            "keywords": ((entry.get("struct_keywords") or {}).get("text")) or "",
            "experimental_method": ((entry.get("rcsb_entry_info") or {}).get("experimental_method")) or "",
            "resolution": (((entry.get("rcsb_entry_info") or {}).get("resolution_combined")) or [None])[0],
            "ligands": ((entry.get("rcsb_entry_info") or {}).get("nonpolymer_bound_components")) or [],
            "doi": ((entry.get("rcsb_primary_citation") or {}).get("pdbx_database_id_DOI")) or "",
            "pubmed_id": ((entry.get("rcsb_primary_citation") or {}).get("pdbx_database_id_PubMed")) or "",
            "polymer_entities": summarized_entities,
            "uniprot_ids": sorted({uid for entity in summarized_entities for uid in entity.get("uniprot_ids", [])}),
            "organisms": sorted({org for entity in summarized_entities for org in entity.get("organisms", [])}),
        }

    def _summarize_polymer_entity(self, entity: dict[str, Any]) -> dict[str, Any]:
        identifiers = entity.get("rcsb_polymer_entity_container_identifiers") or {}
        source = entity.get("rcsb_entity_source_organism") or []
        return {
            "entity_id": identifiers.get("entity_id", ""),
            "chains": identifiers.get("auth_asym_ids") or identifiers.get("asym_ids") or [],
            "description": ((entity.get("rcsb_polymer_entity") or {}).get("pdbx_description")) or "",
            "uniprot_ids": identifiers.get("uniprot_ids") or [],
            "gene_names": sorted(
                {
                    gene_name.get("value")
                    for item in source
                    for gene_name in _safe_list(item.get("rcsb_gene_name"))
                    if isinstance(gene_name, dict) and gene_name.get("value")
                }
            ),
            "organisms": sorted(
                {
                    item.get("scientific_name") or item.get("ncbi_scientific_name")
                    for item in source
                    if item.get("scientific_name") or item.get("ncbi_scientific_name")
                }
            ),
        }

    def _matches_target(self, summary: dict[str, Any], *, target: str, accession: str) -> bool:
        target_upper = target.upper()
        if accession and accession in summary.get("uniprot_ids", []):
            return True
        for entity in summary.get("polymer_entities", []):
            if any(target_upper == gene.upper() for gene in entity.get("gene_names", [])):
                return True
            if target_upper in (entity.get("description", "") or "").upper():
                return True
        if target_upper in (summary.get("title", "") or "").upper():
            return True
        return False


class SabdabClient:
    """Use SAbDab's public summary-file endpoints for antibody structure context."""

    BASE_URL = "https://opig.stats.ox.ac.uk/webapps/sabdab-sabpred/sabdab"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def describe(self) -> dict[str, Any]:
        return {
            "name": "SAbDab summary endpoint",
            "base_url": self.BASE_URL,
            "capabilities": [
                "pdb_summary_lookup",
                "antigen_and_affinity_summary",
            ],
        }

    def get_pdb_summary(self, pdb_id: str) -> dict[str, Any] | None:
        pdb_id = pdb_id.lower()
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(f"{self.BASE_URL}/summary/{pdb_id}/")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        reader = csv.DictReader(io.StringIO(response.text), delimiter="\t")
        rows = list(reader)
        if not rows:
            return None
        return {
            "pdb_id": pdb_id,
            "records": rows,
            "record_count": len(rows),
            "antigen_names": sorted(
                {
                    row.get("antigen_name", "")
                    for row in rows
                    if row.get("antigen_name") and row.get("antigen_name") != "NA"
                }
            ),
            "antigen_types": sorted(
                {
                    row.get("antigen_type", "")
                    for row in rows
                    if row.get("antigen_type")
                }
            ),
            "affinities": [
                {
                    "affinity": row.get("affinity"),
                    "delta_g": row.get("delta_g"),
                    "method": row.get("affinity_method"),
                    "temperature": row.get("temperature"),
                }
                for row in rows
                if row.get("affinity") or row.get("delta_g")
            ],
        }

    def lookup_many(self, pdb_ids: list[str], *, limit: int = 6) -> list[dict[str, Any]]:
        hits = []
        seen: set[str] = set()
        for pdb_id in pdb_ids:
            normalized = pdb_id.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            summary = self.get_pdb_summary(normalized)
            if summary:
                hits.append(summary)
            if len(hits) >= limit:
                break
        return hits
