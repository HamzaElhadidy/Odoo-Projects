from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    enable_chef_commission = fields.Boolean(
        string="Enable Chef Commission",
        default=False,
        help="Enable or disable the Chef Commission feature for this company. "
             "When disabled, the Chef field on sale orders, the Is Chef checkbox, "
             "and the Chef Commission tab on contacts will all be hidden. "
             "The scheduler will also skip this company.",
    )

    commission_calculation = fields.Selection([
        ('agent', 'By Chef'),
    ], string="Commission Calculation")

    commission_based_on = fields.Selection([
        ('sell_price', 'Sell Price'),
    ], string="Commission Based On")

    apply_commission_with = fields.Selection([
        ('sale_order', 'Sale Order'),  # kept for backward compatibility
        ('invoice',    'Invoice'),
    ], string="Apply Commission With")

    commission_account_id = fields.Many2one(
        'account.account',
        string="Commission Account",
        help="Default account for chef commission entries.",
    )