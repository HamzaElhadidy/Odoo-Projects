from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    commission_account_id = fields.Many2one(
        'account.account',
        string="Commission Account",
        domain=[('deprecated', '=', False)],
        help="Default account used when posting agent commission journal entries.",
    )
    commission_calculation = fields.Selection([
        ('agent', 'By Chef'),
    ],
        string="Commission Calculation",
        default='agent',
    )
    commission_based_on = fields.Selection([
        ('sell_price',    'Sell Price'),
    ],
        string="Commission Based On",
        default='sell_price',
    )
    apply_commission_with = fields.Selection([
        ('invoice',    'Invoice'),
    ],
        string="Apply Commission With",
        default='sale_order',
    )