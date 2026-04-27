"""
DrugMind Molecular Service
分子3D坐标生成 + 增强ADMET预测
优先使用RDKit, 降级到PubChem REST API
"""

import logging
import json
import urllib.request
import urllib.parse
from typing import Optional

logger = logging.getLogger(__name__)

# Try importing RDKit
try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, QED, AllChem, Draw
    from rdkit.Chem.rdMolDescriptors import CalcTPSA, CalcNumRotatableBonds
    RDKIT_AVAILABLE = True
    logger.info("RDKit available for molecular operations")
except ImportError:
    RDKIT_AVAILABLE = False
    logger.warning("RDKit not available, using PubChem API fallback")


class MolecularService:
    """分子服务: 3D坐标生成 + ADMET预测"""

    def __init__(self):
        self.rdkit = RDKIT_AVAILABLE

    def smiles_to_sdf(self, smiles: str, optimize: bool = True) -> dict:
        """
        SMILES -> SDF (3D坐标)
        Returns: {"sdf": "...", "source": "rdkit"|"pubchem", "success": bool}
        """
        # Try RDKit first
        if self.rdkit:
            return self._rdkit_sdf(smiles, optimize)
        # Fallback to PubChem
        return self._pubchem_sdf(smiles)

    def _rdkit_sdf(self, smiles: str, optimize: bool) -> dict:
        """使用RDKit生成3D SDF"""
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {"success": False, "error": "Invalid SMILES"}

            mol = Chem.AddHs(mol)
            params = AllChem.ETKDGv3()
            params.randomSeed = 42
            embed_result = AllChem.EmbedMolecule(mol, params)
            if embed_result != 0:
                # Try with more attempts
                params.maxIterations = 1000
                params.useRandomCoords = True
                embed_result = AllChem.EmbedMolecule(mol, params)

            if optimize and embed_result == 0:
                AllChem.MMFFOptimizeMolecule(mol, maxIters=500)

            sdf = Chem.MolToMolBlock(mol)
            return {"success": True, "sdf": sdf, "source": "rdkit"}
        except Exception as e:
            logger.error(f"RDKit SDF generation failed: {e}")
            return self._pubchem_sdf(smiles)

    def _pubchem_sdf(self, smiles: str) -> dict:
        """使用PubChem REST API获取3D SDF"""
        try:
            encoded = urllib.parse.quote(smiles, safe='')
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/SDF?record_type=3d"
            req = urllib.request.Request(url, headers={"User-Agent": "DrugMind/3.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                sdf = resp.read().decode('utf-8')
                return {"success": True, "sdf": sdf, "source": "pubchem"}
        except Exception as e:
            logger.warning(f"PubChem 3D SDF failed: {e}")
            # Try 2D
            try:
                url2d = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/SDF"
                req = urllib.request.Request(url2d, headers={"User-Agent": "DrugMind/3.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    sdf = resp.read().decode('utf-8')
                    return {"success": True, "sdf": sdf, "source": "pubchem-2d"}
            except Exception as e2:
                return {"success": False, "error": f"All sources failed: {e2}"}

    def predict_admet(self, smiles: str) -> dict:
        """
        增强ADMET预测
        RDKit可用时: 完整描述符计算
        RDKit不可用时: PubChem API获取属性
        """
        if self.rdkit:
            return self._rdkit_admet(smiles)
        return self._pubchem_admet(smiles)

    def _rdkit_admet(self, smiles: str) -> dict:
        """RDKit完整ADMET预测"""
        try:
            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {"error": "Invalid SMILES"}

            mw = round(Descriptors.MolWt(mol), 1)
            logp = round(Descriptors.MolLogP(mol), 2)
            hbd = Descriptors.NumHDonors(mol)
            hba = Descriptors.NumHAcceptors(mol)
            tpsa = round(Descriptors.TPSA(mol), 1)
            qed = round(QED.qed(mol), 3)
            rotbonds = Descriptors.NumRotatableBonds(mol)
            rings = Descriptors.RingCount(mol)
            aromatic_rings = Descriptors.NumAromaticRings(mol)
            heavy_atoms = Descriptors.HeavyAtomCount(mol)

            # Lipinski violations
            lipinski_violations = sum([
                mw > 500, logp > 5, hbd > 5, hba > 10
            ])

            # SA Score approximation
            sa_score = round(1 + rings * 0.5 + rotbonds * 0.1, 1)

            # Drug-likeness assessment
            drug_like = lipinski_violations == 0 and tpsa < 140 and sa_score < 6

            # Bioavailability score
            bioavailability = "high" if lipinski_violations == 0 and tpsa < 120 else (
                "moderate" if lipinski_violations <= 1 else "low"
            )

            # CNS MPO (multiparameter optimization) - simplified
            cns_mpo = round(max(0, min(6,
                (500 - mw) / 200 + (5 - logp) / 2 + (120 - tpsa) / 40 +
                (5 - hbd) / 2 + (0.3 if mw < 360 else 0) + (0.3 if logp < 3 else 0)
            )), 1)

            return {
                "smiles": smiles,
                "mw": mw,
                "logp": logp,
                "hbd": hbd,
                "hba": hba,
                "tpsa": tpsa,
                "qed": qed,
                "rotatable_bonds": rotbonds,
                "rings": rings,
                "aromatic_rings": aromatic_rings,
                "heavy_atoms": heavy_atoms,
                "sa_score": sa_score,
                "lipinski_violations": lipinski_violations,
                "drug_like": drug_like,
                "bioavailability": bioavailability,
                "cns_mpo": cns_mpo,
                "source": "rdkit",
            }
        except Exception as e:
            logger.error(f"RDKit ADMET failed: {e}")
            return {"error": str(e)}

    def _pubchem_admet(self, smiles: str) -> dict:
        """PubChem API获取分子属性"""
        try:
            encoded = urllib.parse.quote(smiles, safe='')
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/property/MolecularFormula,MolecularWeight,XLogP,HBondDonorCount,HBondAcceptorCount,TPSA,RotatableBondCount,HeavyAtomCount,RingCount,Complexity/JSON"
            req = urllib.request.Request(url, headers={"User-Agent": "DrugMind/3.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                props = data["PropertyTable"]["Properties"][0]

                mw = props.get("MolecularWeight", 0)
                logp = props.get("XLogP", 0)
                hbd = props.get("HBondDonorCount", 0)
                hba = props.get("HBondAcceptorCount", 0)
                tpsa = props.get("TPSA", 0)
                rotbonds = props.get("RotatableBondCount", 0)
                rings = props.get("RingCount", 0)
                heavy = props.get("HeavyAtomCount", 0)

                lipinski_violations = sum([
                    mw > 500, (logp or 0) > 5, hbd > 5, hba > 10
                ])

                return {
                    "smiles": smiles,
                    "mw": mw,
                    "logp": logp,
                    "hbd": hbd,
                    "hba": hba,
                    "tpsa": tpsa,
                    "qed": None,
                    "rotatable_bonds": rotbonds,
                    "rings": rings,
                    "heavy_atoms": heavy,
                    "sa_score": None,
                    "lipinski_violations": lipinski_violations,
                    "drug_like": lipinski_violations == 0 and tpsa < 140,
                    "bioavailability": "high" if lipinski_violations == 0 else "moderate",
                    "source": "pubchem",
                }
        except Exception as e:
            logger.error(f"PubChem ADMET failed: {e}")
            return {"error": str(e)}

    def get_mol_info(self, smiles: str) -> dict:
        """获取分子基本信息（名称、分子式等）"""
        try:
            encoded = urllib.parse.quote(smiles, safe='')
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{encoded}/property/MolecularFormula,MolecularWeight,IUPACName/JSON"
            req = urllib.request.Request(url, headers={"User-Agent": "DrugMind/3.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                props = data["PropertyTable"]["Properties"][0]
                return {
                    "smiles": smiles,
                    "formula": props.get("MolecularFormula", ""),
                    "mw": props.get("MolecularWeight", 0),
                    "iupac_name": props.get("IUPACName", ""),
                    "cid": props.get("CID", 0),
                }
        except Exception as e:
            return {"smiles": smiles, "error": str(e)}


# Singleton
_mol_service = None

def get_mol_service() -> MolecularService:
    global _mol_service
    if _mol_service is None:
        _mol_service = MolecularService()
    return _mol_service
