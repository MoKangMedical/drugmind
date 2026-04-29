"""
DrugMind SaaS Module
Stripe支付 + 多租户 + 分身市场 + SSO
"""

import os
import json
import logging
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Multi-Tenant Architecture
# ═══════════════════════════════════════════

@dataclass
class Tenant:
    tenant_id: str
    name: str
    plan: str  # starter, team, enterprise
    seats: int
    owner_id: str
    created_at: str = ""
    stripe_customer_id: str = ""
    stripe_subscription_id: str = ""
    sso_enabled: bool = False
    sso_provider: str = ""  # okta, azure, google
    sso_config: dict = field(default_factory=dict)
    settings: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class TenantManager:
    """多租户管理"""

    def __init__(self, storage_dir: str = "./drugmind_data/tenants"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.tenants: dict[str, Tenant] = {}
        self._load()

    def _load(self):
        path = f"{self.storage_dir}/tenants.json"
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                for tid, tdata in data.items():
                    self.tenants[tid] = Tenant(**tdata)

    def _save(self):
        path = f"{self.storage_dir}/tenants.json"
        with open(path, "w") as f:
            json.dump({tid: asdict(t) for tid, t in self.tenants.items()}, f, indent=2, ensure_ascii=False)

    def create(self, name: str, plan: str, owner_id: str, seats: int = 0) -> Tenant:
        tenant_id = f"t_{secrets.token_hex(8)}"
        plan_seats = {"starter": 5, "team": 50, "enterprise": 999}
        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            plan=plan,
            seats=seats or plan_seats.get(plan, 5),
            owner_id=owner_id,
        )
        self.tenants[tenant_id] = tenant
        self._save()
        return tenant

    def get(self, tenant_id: str) -> Optional[Tenant]:
        return self.tenants.get(tenant_id)

    def update_plan(self, tenant_id: str, plan: str):
        if tenant_id in self.tenants:
            self.tenants[tenant_id].plan = plan
            self._save()

    def list_all(self) -> list[dict]:
        return [{"tenant_id": t.tenant_id, "name": t.name, "plan": t.plan, "seats": t.seats} for t in self.tenants.values()]


# ═══════════════════════════════════════════
# Stripe Integration
# ═══════════════════════════════════════════

STRIPE_PRICES = {
    "starter": os.getenv("STRIPE_PRICE_STARTER", "price_starter_monthly"),
    "team": os.getenv("STRIPE_PRICE_TEAM", "price_team_monthly"),
    "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE", "price_enterprise_monthly"),
}


class StripeService:
    """Stripe支付集成"""

    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY", "")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        self.enabled = bool(self.api_key)

    def create_checkout_session(self, tenant_id: str, plan: str, success_url: str, cancel_url: str) -> dict:
        """创建Stripe Checkout会话"""
        if not self.enabled:
            return self._mock_checkout(tenant_id, plan)

        try:
            import stripe
            stripe.api_key = self.api_key

            session = stripe.checkout.Session.create(
                mode="subscription",
                payment_method_types=["card"],
                line_items=[{"price": STRIPE_PRICES.get(plan), "quantity": 1}],
                success_url=f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=cancel_url,
                metadata={"tenant_id": tenant_id, "plan": plan},
            )
            return {"checkout_url": session.url, "session_id": session.id}
        except Exception as e:
            logger.error(f"Stripe checkout failed: {e}")
            return {"error": str(e)}

    def create_portal_session(self, customer_id: str, return_url: str) -> dict:
        """创建Stripe客户门户"""
        if not self.enabled:
            return {"portal_url": f"{return_url}?mock=true"}

        try:
            import stripe
            stripe.api_key = self.api_key
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url,
            )
            return {"portal_url": session.url}
        except Exception as e:
            return {"error": str(e)}

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """处理Stripe webhook"""
        if not self.enabled:
            return {"status": "mock"}

        try:
            import stripe
            stripe.api_key = self.api_key
            event = stripe.Webhook.construct_event(payload, sig_header, self.webhook_secret)

            if event["type"] == "checkout.session.completed":
                session = event["data"]["object"]
                return {"type": "checkout_completed", "tenant_id": session["metadata"].get("tenant_id"), "customer_id": session.get("customer")}
            elif event["type"] == "customer.subscription.updated":
                sub = event["data"]["object"]
                return {"type": "subscription_updated", "status": sub["status"]}
            elif event["type"] == "customer.subscription.deleted":
                return {"type": "subscription_cancelled"}

            return {"type": event["type"]}
        except Exception as e:
            return {"error": str(e)}

    def _mock_checkout(self, tenant_id: str, plan: str) -> dict:
        """Mock checkout for development"""
        return {
            "checkout_url": f"#mock-checkout?plan={plan}&tenant={tenant_id}",
            "session_id": f"cs_mock_{secrets.token_hex(8)}",
            "mock": True,
        }


# ═══════════════════════════════════════════
# Twin Marketplace (分身市场)
# ═══════════════════════════════════════════

@dataclass
class MarketplaceTwin:
    twin_id: str
    name: str
    role: str
    description: str
    author: str
    author_id: str
    expertise: list[str] = field(default_factory=list)
    downloads: int = 0
    rating: float = 0.0
    rating_count: int = 0
    created_at: str = ""
    public: bool = True

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class TwinMarketplace:
    """分身市场: 分享和下载AI数字分身"""

    def __init__(self, storage_dir: str = "./drugmind_data/marketplace"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.twins: dict[str, MarketplaceTwin] = {}
        self._load()

    def _load(self):
        path = f"{self.storage_dir}/twins.json"
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
                for tid, tdata in data.items():
                    self.twins[tid] = MarketplaceTwin(**tdata)

    def _save(self):
        path = f"{self.storage_dir}/twins.json"
        with open(path, "w") as f:
            json.dump({tid: asdict(t) for tid, t in self.twins.items()}, f, indent=2, ensure_ascii=False)

    def publish(self, name: str, role: str, description: str, author: str,
                author_id: str, expertise: list[str] = None) -> MarketplaceTwin:
        """发布分身到市场"""
        twin_id = f"mt_{secrets.token_hex(6)}"
        twin = MarketplaceTwin(
            twin_id=twin_id, name=name, role=role,
            description=description, author=author,
            author_id=author_id, expertise=expertise or [],
        )
        self.twins[twin_id] = twin
        self._save()
        return twin

    def search(self, query: str = "", role: str = "", limit: int = 20) -> list[dict]:
        """搜索市场分身"""
        results = []
        for t in self.twins.values():
            if not t.public:
                continue
            if query and query.lower() not in t.name.lower() and query.lower() not in t.description.lower():
                continue
            if role and t.role != role:
                continue
            results.append(asdict(t))
        results.sort(key=lambda x: x["downloads"], reverse=True)
        return results[:limit]

    def download(self, twin_id: str) -> Optional[dict]:
        """下载分身（增加下载计数）"""
        if twin_id in self.twins:
            self.twins[twin_id].downloads += 1
            self._save()
            return asdict(self.twins[twin_id])
        return None

    def rate(self, twin_id: str, score: float) -> bool:
        """评分"""
        if twin_id in self.twins and 1 <= score <= 5:
            t = self.twins[twin_id]
            total = t.rating * t.rating_count + score
            t.rating_count += 1
            t.rating = round(total / t.rating_count, 1)
            self._save()
            return True
        return False

    def trending(self) -> list[dict]:
        """热门分身"""
        return sorted(
            [asdict(t) for t in self.twins.values() if t.public],
            key=lambda x: x["downloads"],
            reverse=True
        )[:10]


# ═══════════════════════════════════════════
# SSO Integration (Enterprise)
# ═══════════════════════════════════════════

class SSOService:
    """SSO集成 (SAML/OIDC)"""

    PROVIDERS = {
        "okta": {"name": "Okta", "type": "oidc"},
        "azure": {"name": "Azure AD", "type": "oidc"},
        "google": {"name": "Google Workspace", "type": "oidc"},
        "onelogin": {"name": "OneLogin", "type": "saml"},
    }

    def get_provider_config(self, provider: str) -> dict:
        """获取SSO提供商配置模板"""
        return self.PROVIDERS.get(provider, {})

    def initiate_sso(self, tenant_id: str, provider: str, redirect_uri: str) -> dict:
        """发起SSO登录"""
        config = self.get_provider_config(provider)
        if not config:
            return {"error": f"Unsupported provider: {provider}"}

        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)

        return {
            "provider": provider,
            "auth_url": f"https://{provider}.example.com/authorize",
            "state": state,
            "redirect_uri": redirect_uri,
            "note": "Configure your IdP with the provided redirect_uri",
        }

    def handle_callback(self, tenant_id: str, provider: str, code: str) -> dict:
        """处理SSO回调"""
        # In production, exchange code for tokens and validate
        return {
            "status": "success",
            "user": {"email": f"user@{provider}.example.com"},
            "note": "Implement actual token exchange for production",
        }


# ═══════════════════════════════════════════
# Singletons
# ═══════════════════════════════════════════

_tenant_mgr = None
_stripe_svc = None
_marketplace = None
_sso_svc = None

def get_tenant_manager() -> TenantManager:
    global _tenant_mgr
    if _tenant_mgr is None:
        _tenant_mgr = TenantManager()
    return _tenant_mgr

def get_stripe_service() -> StripeService:
    global _stripe_svc
    if _stripe_svc is None:
        _stripe_svc = StripeService()
    return _stripe_svc

def get_marketplace() -> TwinMarketplace:
    global _marketplace
    if _marketplace is None:
        _marketplace = TwinMarketplace()
    return _marketplace

def get_sso_service() -> SSOService:
    global _sso_svc
    if _sso_svc is None:
        _sso_svc = SSOService()
    return _sso_svc
