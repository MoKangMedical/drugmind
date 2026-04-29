"""
Digital Twin Engine — 数字孪生引擎
药物分子模拟、靶点对接、虚拟筛选
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json
import math
import random


@dataclass
class Molecule:
    """分子定义"""
    name: str
    smiles: str
    molecular_weight: float
    logp: float
    hbd: int  # 氢键供体
    hba: int  # 氢键受体
    tpsa: float  # 拓扑极性表面积


@dataclass
class Target:
    """靶点定义"""
    name: str
    gene: str
    pdb_id: str
    binding_site: Dict
    druggability: float


@dataclass
class DockingResult:
    """对接结果"""
    molecule: str
    target: str
    binding_affinity: float  # kcal/mol
    ic50_estimate: float  # nM
    interactions: List[str]
    pose: Dict


class DigitalTwinEngine:
    """数字孪生引擎"""
    
    def __init__(self):
        self.molecules: Dict[str, Molecule] = {}
        self.targets: Dict[str, Target] = {}
        self.docking_results: List[DockingResult] = []
    
    def add_molecule(self, molecule: Molecule):
        """添加分子"""
        self.molecules[molecule.name] = molecule
    
    def add_target(self, target: Target):
        """添加靶点"""
        self.targets[target.name] = target
    
    def predict_binding_affinity(self, molecule_name: str, target_name: str) -> float:
        """预测结合亲和力"""
        mol = self.molecules.get(molecule_name)
        target = self.targets.get(target_name)
        
        if not mol or not target:
            return 0.0
        
        # 基于分子描述符的简化预测模型
        score = -8.0  # 基准结合能
        
        # 分子量影响
        if 300 <= mol.molecular_weight <= 500:
            score -= 0.5
        
        # LogP影响
        if 1.0 <= mol.logp <= 3.0:
            score -= 0.3
        
        # 氢键影响
        if mol.hbd <= 5 and mol.hba <= 10:
            score -= 0.2
        
        # 靶点可药性影响
        score *= target.druggability
        
        # 添加模拟波动
        score += random.gauss(0, 0.3)
        
        return round(score, 2)
    
    def estimate_ic50(self, binding_affinity: float) -> float:
        """估算IC50"""
        # ΔG = RT ln(IC50/Kd)
        # 简化转换
        ic50 = math.exp(-binding_affinity * 1000 / (8.314 * 298)) * 1000
        return round(ic50, 2)
    
    def virtual_screen(self, target_name: str, top_n: int = 10) -> List[Dict]:
        """虚拟筛选"""
        results = []
        
        for mol_name, mol in self.molecules.items():
            affinity = self.predict_binding_affinity(mol_name, target_name)
            ic50 = self.estimate_ic50(affinity)
            
            results.append({
                "molecule": mol_name,
                "target": target_name,
                "binding_affinity": affinity,
                "ic50_estimate": ic50,
                "druglikeness": self._check_druglikeness(mol)
            })
        
        # 按结合亲和力排序
        results.sort(key=lambda x: x["binding_affinity"])
        
        return results[:top_n]
    
    def _check_druglikeness(self, molecule: Molecule) -> Dict:
        """检查类药性 (Lipinski's Rule of Five)"""
        violations = 0
        rules = []
        
        if molecule.molecular_weight > 500:
            violations += 1
            rules.append("MW > 500")
        
        if molecule.logp > 5:
            violations += 1
            rules.append("LogP > 5")
        
        if molecule.hbd > 5:
            violations += 1
            rules.append("HBD > 5")
        
        if molecule.hba > 10:
            violations += 1
            rules.append("HBA > 10")
        
        return {
            "pass": violations <= 1,
            "violations": violations,
            "rules_broken": rules
        }
    
    def simulate_docking(self, molecule_name: str, target_name: str) -> DockingResult:
        """模拟分子对接"""
        mol = self.molecules.get(molecule_name)
        target = self.targets.get(target_name)
        
        affinity = self.predict_binding_affinity(molecule_name, target_name)
        ic50 = self.estimate_ic50(affinity)
        
        # 生成模拟的相互作用
        interactions = self._generate_interactions(mol, target)
        
        result = DockingResult(
            molecule=molecule_name,
            target=target_name,
            binding_affinity=affinity,
            ic50_estimate=ic50,
            interactions=interactions,
            pose={"x": 0.0, "y": 0.0, "z": 0.0, "rotation": [0, 0, 0]}
        )
        
        self.docking_results.append(result)
        return result
    
    def _generate_interactions(self, mol: Optional[Molecule], target: Optional[Target]) -> List[str]:
        """生成分子相互作用"""
        interactions = ["Hydrophobic interaction"]
        
        if mol and mol.hbd > 0:
            interactions.append("Hydrogen bond donor")
        if mol and mol.hba > 0:
            interactions.append("Hydrogen bond acceptor")
        
        interactions.append("Van der Waals force")
        
        if target and target.druggability > 0.8:
            interactions.append("Pi-Pi stacking")
        
        return interactions
