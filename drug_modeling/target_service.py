"""
DrugMind Target Discovery Service
整合OpenTargets + ChEMBL + PubMed真实数据
"""

import json
import logging
import urllib.request
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

OPENTARGETS_API = "https://api.platform.opentargets.org/api/v4/graphql"
CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"


class TargetDiscoveryService:
    """靶点发现服务: 整合多个公开数据源"""

    def search_targets(self, disease: str, max_results: int = 10) -> dict:
        """
        搜索疾病相关靶点
        Returns: {"targets": [...], "disease": str, "count": int}
        """
        # Step 1: 通过OpenTargets搜索疾病ID
        disease_id = self._search_disease_id(disease)
        if not disease_id:
            return {"error": f"Disease not found: {disease}", "targets": []}

        # Step 2: 获取疾病关联靶点
        targets = self._get_disease_targets(disease_id, max_results)
        return {
            "disease": disease,
            "disease_id": disease_id,
            "targets": targets,
            "count": len(targets),
        }

    def _search_disease_id(self, disease: str) -> Optional[str]:
        """通过OpenTargets搜索疾病ID"""
        query = """
        query SearchDisease($q: String!) {
            search(queryString: $q, entityNames: ["disease"], page: {index: 0, size: 1}) {
                hits {
                    id
                    name
                    entity
                }
            }
        }
        """
        try:
            result = self._opentargets_query(query, {"q": disease})
            hits = result.get("data", {}).get("search", {}).get("hits", [])
            if hits:
                return hits[0]["id"]
        except Exception as e:
            logger.error(f"Disease search failed: {e}")
        return None

    def _get_disease_targets(self, disease_id: str, max_results: int) -> list:
        """获取疾病关联靶点"""
        query = """
        query DiseaseTargets($id: String!, $size: Int!) {
            disease(efoId: $id) {
                id
                name
                associatedTargets(page: {index: 0, size: $size}) {
                    count
                    rows {
                        target {
                            id
                            approvedSymbol
                            approvedName
                            biotype
                            functionDescriptions
                            subcellularLocations {
                                location
                            }
                        }
                        score
                        datatypeScores {
                            componentId: id
                            score
                        }
                    }
                }
            }
        }
        """
        try:
            result = self._opentargets_query(query, {"id": disease_id, "size": max_results})
            disease_data = result.get("data", {}).get("disease", {})
            rows = disease_data.get("associatedTargets", {}).get("rows", [])

            targets = []
            for row in rows:
                target = row.get("target", {})
                # Get datatype scores
                dt_scores = {d["componentId"]: round(d["score"], 4) for d in row.get("datatypeScores", [])}

                targets.append({
                    "id": target.get("id", ""),
                    "symbol": target.get("approvedSymbol", ""),
                    "name": target.get("approvedName", ""),
                    "biotype": target.get("biotype", ""),
                    "function": (target.get("functionDescriptions") or [""])[0][:200],
                    "subcellular": [s["location"] for s in (target.get("subcellularLocations") or [])[:3]],
                    "association_score": round(row.get("score", 0), 4),
                    "genetic_association": dt_scores.get("genetic_association", 0),
                    "known_drug": dt_scores.get("known_drug", 0),
                    "literature": dt_scores.get("literature", 0),
                    "druggability": self._assess_druggability(target),
                })

            # Sort by association score
            targets.sort(key=lambda x: x["association_score"], reverse=True)
            return targets

        except Exception as e:
            logger.error(f"Target fetch failed: {e}")
            return []

    def get_target_detail(self, target_id: str) -> dict:
        """获取靶点详细信息"""
        query = """
        query TargetDetail($id: String!) {
            target(ensemblId: $id) {
                id
                approvedSymbol
                approvedName
                biotype
                functionDescriptions
                subcellularLocations { location }
                tractability {
                    label
                    modality
                    value
                }
                knownDrugs(size: 10) {
                    uniqueDrugs
                    rows {
                        drug { id name maximumClinicalTrialPhase }
                        phase
                        status
                    }
                }
            }
        }
        """
        try:
            result = self._opentargets_query(query, {"id": target_id})
            target = result.get("data", {}).get("target", {})
            if not target:
                return {"error": "Target not found"}

            drugs = target.get("knownDrugs", {})
            return {
                "id": target["id"],
                "symbol": target["approvedSymbol"],
                "name": target["approvedName"],
                "biotype": target.get("biotype", ""),
                "function": (target.get("functionDescriptions") or [""])[0],
                "subcellular": [s["location"] for s in (target.get("subcellularLocations") or [])],
                "tractability": target.get("tractability", []),
                "known_drugs_count": drugs.get("uniqueDrugs", 0),
                "known_drugs": [
                    {
                        "id": d["drug"]["id"],
                        "name": d["drug"]["name"],
                        "phase": d.get("phase", 0),
                        "status": d.get("status", ""),
                    }
                    for d in (drugs.get("rows") or [])[:10]
                ],
            }
        except Exception as e:
            logger.error(f"Target detail failed: {e}")
            return {"error": str(e)}

    def search_compounds(self, target_id: str, max_results: int = 10) -> dict:
        """搜索靶点相关化合物 (ChEMBL)"""
        try:
            url = f"{CHEMBL_API}/molecule/search.json?target_chembl_id={target_id}&limit={max_results}"
            req = urllib.request.Request(url, headers={"User-Agent": "DrugMind/3.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                molecules = []
                for mol in data.get("molecules", []):
                    molecules.append({
                        "chembl_id": mol.get("molecule_chembl_id", ""),
                        "name": mol.get("pref_name", ""),
                        "max_phase": mol.get("max_phase", 0),
                        "molecular_weight": mol.get("molecular_weight", 0),
                        "canonical_smiles": mol.get("canonical_smiles", ""),
                    })
                return {"target_id": target_id, "compounds": molecules, "count": len(molecules)}
        except Exception as e:
            logger.error(f"ChEMBL compound search failed: {e}")
            return {"target_id": target_id, "compounds": [], "error": str(e)}

    def _assess_druggability(self, target: dict) -> str:
        """评估靶点可成药性"""
        symbol = target.get("approvedSymbol", "")
        biotype = target.get("biotype", "")

        # Simple heuristic based on biotype and known information
        if biotype == "protein_coding":
            return "high"
        elif biotype == "ncRNA":
            return "low"
        else:
            return "medium"

    def _opentargets_query(self, query: str, variables: dict) -> dict:
        """执行OpenTargets GraphQL查询"""
        data = json.dumps({"query": query, "variables": variables}).encode()
        req = urllib.request.Request(
            OPENTARGETS_API,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "DrugMind/3.0",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode())


# Singleton
_target_service = None

def get_target_service() -> TargetDiscoveryService:
    global _target_service
    if _target_service is None:
        _target_service = TargetDiscoveryService()
    return _target_service
