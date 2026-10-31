from __future__ import annotations

from app.core.db import SqlAlchemyUnitOfWork
from app.modules.admin.infrastructure.public import SqlAuditLogRepository
from app.modules.rewards.infrastructure.series_catalog import SqlSeriesCatalog
from app.modules.rewards.infrastructure.shop_repository import SqlShopRepository
from app.modules.rewards.infrastructure.unlock_repository import SqlUnlockRepository
from app.modules.rewards.infrastructure.wallet_repository import SqlWalletRepository


class SqlRewardsUnitOfWork(SqlAlchemyUnitOfWork):
    """Một giao dịch cho ví, sổ, khung, cửa hàng, mở khóa và nhật ký quản trị (F13.06)."""

    wallets: SqlWalletRepository
    unlocks: SqlUnlockRepository
    shop: SqlShopRepository
    series: SqlSeriesCatalog
    audit: SqlAuditLogRepository

    def _init_repositories(self) -> None:
        self.wallets = SqlWalletRepository(self.session)
        self.unlocks = SqlUnlockRepository(self.session)
        self.shop = SqlShopRepository(self.session)
        self.series = SqlSeriesCatalog(self.session)
        self.audit = SqlAuditLogRepository(self.session)
