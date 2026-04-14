"""
ADMET预测桥接
调用MediPharma的ADMET引擎或独立运行
"""

import logging
import os
from typing import Optional

from integrations import MediPharmaClient

logger = logging.getLogger(__name__)


class ADMETBridge:
    """ADMET预测桥接层"""

    def __init__(self, medipharma_api_url: str = ""):
        configured_url = (
            medipharma_api_url
            or os.getenv("MEDI_PHARMA_BASE_URL", "").strip()
            or os.getenv("MEDIPHARMA_BASE_URL", "").strip()
        )
        self.api_url = configured_url.rstrip("/")
        self.client = MediPharmaClient(base_url=self.api_url)

    def predict(self, smiles: str) -> dict:
        """ADMET预测"""
        if self.api_url:
            return self._call_api(smiles)
        return self._local_predict(smiles)

    def _call_api(self, smiles: str) -> dict:
        """调用MediPharma API"""
        try:
            return self.client.predict_admet({"smiles": smiles})
        except Exception as e:
            logger.error(f"MediPharma API调用失败: {e}")
            return {"error": str(e)}

    def _local_predict(self, smiles: str) -> dict:
        """本地简化预测"""
        try:
            from rdkit import Chem
            from rdkit.Chem import Descriptors, QED

            mol = Chem.MolFromSmiles(smiles)
            if not mol:
                return {"error": "无效SMILES"}

            return {
                "smiles": smiles,
                "mw": round(Descriptors.MolWt(mol), 1),
                "logp": round(Descriptors.MolLogP(mol), 2),
                "hbd": Descriptors.NumHDonors(mol),
                "hba": Descriptors.NumHAcceptors(mol),
                "tpsa": round(Descriptors.TPSA(mol), 1),
                "qed": round(QED.qed(mol), 3),
                "sa_score": round(1 + Descriptors.RingCount(mol) * 0.5, 1),
                "lipinski_violations": sum([
                    Descriptors.MolWt(mol) > 500,
                    Descriptors.MolLogP(mol) > 5,
                    Descriptors.NumHDonors(mol) > 5,
                    Descriptors.NumHAcceptors(mol) > 10,
                ]),
            }
        except ImportError:
            return {"smiles": smiles, "note": "RDKit未安装，无法本地预测"}
