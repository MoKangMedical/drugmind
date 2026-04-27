"""
DrugMind v3.0 Unit Tests
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRoles:
    """Test role definitions"""

    def test_list_roles(self):
        from digital_twin.roles import list_roles
        roles = list_roles()
        assert len(roles) == 5
        role_ids = [r["role_id"] for r in roles]
        assert "medicinal_chemist" in role_ids
        assert "biologist" in role_ids
        assert "pharmacologist" in role_ids
        assert "data_scientist" in role_ids
        assert "project_lead" in role_ids

    def test_get_role(self):
        from digital_twin.roles import get_role
        role = get_role("medicinal_chemist")
        assert role.display_name == "药物化学家"
        assert role.emoji == "🧪"
        assert role.risk_tolerance < 0.5  # conservative

    def test_role_expertise(self):
        from digital_twin.roles import get_role
        role = get_role("biologist")
        assert "靶点验证" in role.expertise


class TestDigitalTwinEngine:
    """Test digital twin engine"""

    def test_create_twin(self):
        from digital_twin.engine import DigitalTwinEngine
        engine = DigitalTwinEngine(use_llm=False)
        result = engine.create_twin("medicinal_chemist", "TestChemist")
        assert result["status"] == "created"
        assert result["twin_id"] == "medicinal_chemist_TestChemist"

    def test_list_twins(self):
        from digital_twin.engine import DigitalTwinEngine
        engine = DigitalTwinEngine(use_llm=False)
        engine.create_twin("biologist", "TestBio")
        twins = engine.list_twins()
        assert len(twins) >= 1

    def test_ask_twin_template(self):
        from digital_twin.engine import DigitalTwinEngine
        engine = DigitalTwinEngine(use_llm=False)
        engine.create_twin("pharmacologist", "TestPharma")
        resp = engine.ask_twin("pharmacologist_TestPharma", "Is this compound safe?")
        assert resp.message  # Should have template response
        assert resp.confidence == 0.3  # template confidence


class TestPersonality:
    """Test personality system"""

    def test_create_profile(self):
        from digital_twin.personality import PersonalityManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PersonalityManager(tmpdir)
            profile = mgr.create_twin("data_scientist", "TestData")
            assert profile.role_id == "data_scientist"

    def test_system_prompt(self):
        from digital_twin.personality import PersonalityManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = PersonalityManager(tmpdir)
            mgr.create_twin("medicinal_chemist", "TestChemist")
            prompt = mgr.get_system_prompt("medicinal_chemist_TestChemist")
            assert "药物化学家" in prompt or "药物" in prompt


class TestMolecularService:
    """Test molecular service"""

    def test_pubchem_admet(self):
        from drug_modeling.molecular_service import MolecularService
        svc = MolecularService()
        # Force PubChem path
        svc.rdkit = False
        result = svc._pubchem_admet("CC(=O)Oc1ccccc1C(=O)O")  # Aspirin
        if "error" not in result:
            assert result["mw"] > 0
            assert result["hbd"] >= 0

    def test_mol_info(self):
        from drug_modeling.molecular_service import MolecularService
        svc = MolecularService()
        result = svc.get_mol_info("CCO")  # Ethanol
        if "error" not in result:
            assert result["formula"]


class TestTargetService:
    """Test target discovery service"""

    def test_search_disease(self):
        from drug_modeling.target_service import TargetDiscoveryService
        svc = TargetDiscoveryService()
        result = svc.search_targets("lung cancer", 3)
        assert result.get("disease")
        assert isinstance(result.get("targets", []), list)


class TestKanban:
    """Test project kanban"""

    def test_create_project(self):
        from project.kanban import KanbanBoard
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            board = KanbanBoard(tmpdir)
            project = board.create_project("test_proj", "Test Project", target="EGFR")
            assert project.project_id == "test_proj"


class TestCompoundTracker:
    """Test compound tracker"""

    def test_add_compound(self):
        from drug_modeling.compound_tracker import CompoundTracker
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = CompoundTracker(tmpdir)
            comp = tracker.add_compound("C001", "CCO", name="Ethanol")
            assert comp.compound_id == "C001"


class TestUserManager:
    """Test user management"""

    def test_register_login(self):
        from auth.user import UserManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = UserManager(tmpdir)
            result = mgr.register("testuser", "test@test.com", "password123", "Test User")
            assert "error" not in result
            login = mgr.login("testuser", "password123")
            assert "error" not in login


class TestSaaS:
    """Test SaaS module"""

    def test_tenant_manager(self):
        from api.saas import TenantManager
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = TenantManager(tmpdir)
            tenant = mgr.create("TestOrg", "team", "owner1")
            assert tenant.plan == "team"
            assert mgr.get(tenant.tenant_id)

    def test_marketplace(self):
        from api.saas import TwinMarketplace
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            mp = TwinMarketplace(tmpdir)
            twin = mp.publish("Expert Chemist", "medicinal_chemist", "Synthesis expert", "Author", "a1")
            assert twin.twin_id
            results = mp.search("Chemist")
            assert len(results) >= 1

    def test_stripe_mock(self):
        from api.saas import StripeService
        svc = StripeService()
        result = svc.create_checkout_session("t1", "team", "/", "/")
        assert result.get("mock") or result.get("checkout_url")

    def test_sso_service(self):
        from api.saas import SSOService
        svc = SSOService()
        result = svc.initiate_sso("t1", "okta", "/callback")
        assert result.get("provider") == "okta"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
