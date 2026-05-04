"""
Migration: Add commission_billed field to sale.order
Run this once after deploying the updated module.

Place this file at:
  waly_chef_commission/migrations/15.0.1.1.0/post-migrate.py
  (adjust version to match your module version in __manifest__.py)
"""

import logging
_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """
    Mark existing sale orders as commission_billed=True if their agent's
    commission is already in 'bill_created' or 'paid' state.
    This prevents old orders from being double-billed after the upgrade.
    """
    _logger.info("Chef Commission migration: setting commission_billed on existing orders...")

    # All orders linked to a commission that already has a bill
    cr.execute("""
        UPDATE sale_order so
        SET commission_billed = TRUE
        FROM chef_commission cc
        WHERE so.agent_id = cc.id
          AND cc.state IN ('bill_created', 'paid')
          AND so.commission_billed IS NOT TRUE
    """)

    _logger.info(
        "Chef Commission migration: updated %d sale order(s) to commission_billed=True.",
        cr.rowcount
    )