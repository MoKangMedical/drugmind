"""
BY-inspired screening and ranking adapted for DrugMind small molecules.
"""

from __future__ import annotations

from typing import Any


class ScreeningBridge:
    """Composite ranking layer for DrugMind DMTA cycles."""

    def score_compound(self, compound: dict[str, Any]) -> dict[str, Any]:
        activity = float(compound.get("activity_pIC50") or 0.0)
        qed = float(compound.get("qed") or 0.0)
        lipinski = int(compound.get("lipinski_violations") or 0)
        logp = float(compound.get("logp") or 0.0)
        mw = float(compound.get("mw") or 0.0)
        admet_score = float(compound.get("admet_score") or 0.0)

        potency_score = min(max((activity - 4.5) / 3.5, 0.0), 1.0)
        qed_score = min(max(qed, 0.0), 1.0)
        admet_bonus = min(max(admet_score, 0.0), 1.0)
        liability_penalty = (lipinski * 0.12) + max(logp - 3.8, 0.0) * 0.05 + max(mw - 500.0, 0.0) / 1200.0
        developability = max(0.0, 1.0 - liability_penalty)
        composite = round(
            (0.42 * potency_score)
            + (0.28 * qed_score)
            + (0.20 * developability)
            + (0.10 * admet_bonus),
            4,
        )
        verdict = "advance" if composite >= 0.68 else "rescue" if composite >= 0.5 else "stop"
        return {
            **compound,
            "screening_score": composite,
            "potency_score": round(potency_score, 4),
            "developability_score": round(developability, 4),
            "verdict": verdict,
        }

    def screen_series(self, compounds: list[dict[str, Any]]) -> dict[str, Any]:
        ranked = [self.score_compound(compound) for compound in compounds]
        ranked.sort(key=lambda item: item.get("screening_score", 0.0), reverse=True)
        shortlist = [item for item in ranked if item["verdict"] == "advance"][:8]
        rescue_bucket = [item for item in ranked if item["verdict"] == "rescue"][:6]
        stop_bucket = [item for item in ranked if item["verdict"] == "stop"][:10]
        attrition = {
            "input_compounds": len(compounds),
            "advance": len([item for item in ranked if item["verdict"] == "advance"]),
            "rescue": len(rescue_bucket),
            "stop": len(stop_bucket),
        }
        return {
            "ranked_compounds": ranked,
            "shortlist": shortlist,
            "rescue_bucket": rescue_bucket,
            "stop_bucket": stop_bucket,
            "attrition": attrition,
        }

    def pareto_front(self, compounds: list[dict[str, Any]]) -> list[dict[str, Any]]:
        scored = [self.score_compound(compound) for compound in compounds]
        front: list[dict[str, Any]] = []
        for item in scored:
            dominated = False
            for other in scored:
                if other is item:
                    continue
                if (
                    other.get("activity_pIC50", 0.0) >= item.get("activity_pIC50", 0.0)
                    and other.get("qed", 0.0) >= item.get("qed", 0.0)
                    and other.get("lipinski_violations", 99) <= item.get("lipinski_violations", 99)
                    and (
                        other.get("activity_pIC50", 0.0) > item.get("activity_pIC50", 0.0)
                        or other.get("qed", 0.0) > item.get("qed", 0.0)
                        or other.get("lipinski_violations", 99) < item.get("lipinski_violations", 99)
                    )
                ):
                    dominated = True
                    break
            if not dominated:
                front.append(item)
        front.sort(key=lambda item: item.get("screening_score", 0.0), reverse=True)
        return front
