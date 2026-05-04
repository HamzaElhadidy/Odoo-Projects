import logging
_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """
    After module install/update, sync group_chef_commission_active
    for all companies so the menu reflects the current toggle state.
    """
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})

    companies = env['res.company'].search([])
    companies._sync_chef_commission_group()
    _logger.info("Chef Commission: group sync completed for %d companies.", len(companies))