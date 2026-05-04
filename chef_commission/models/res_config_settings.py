from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_calculation = fields.Selection([
        ('agent',            'By Chef'),
    ],
        string="Commission Calculation",
        related='company_id.commission_calculation',
        readonly=False,
    )
    commission_based_on = fields.Selection([
        ('sell_price',    'Sell Price'),
    ],
        string="Commission Based On",
        related='company_id.commission_based_on',
        readonly=False,
    )
    apply_commission_with = fields.Selection([
        ('invoice',    'Invoice'),
    ],
        string="Apply Commission With",
        related='company_id.apply_commission_with',
        readonly=False,
    )
    commission_account_id = fields.Many2one(
        related='company_id.commission_account_id',
        string="Commission Account",
        readonly=False,
    )