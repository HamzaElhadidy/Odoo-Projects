from odoo import models, fields


class ChefCommissionHistory(models.Model):
    _name = 'chef.commission.history'
    _description = 'Chef Commission History'
    _order = 'date desc, id desc'

    commission_id = fields.Many2one(
        'chef.commission', string="Commission",
        ondelete='cascade', index=True)

    date = fields.Datetime(
        string="Date",
        default=fields.Datetime.now,
        readonly=True)

    event = fields.Selection([
        ('bill_created', 'Bill Created'),
        ('paid',         'Paid'),
        ('auto_payment', 'Auto Payment'),
        ('reset',        'Reset to Draft'),
        ('cancelled',    'Cancelled'),
        ('cycle',        'New Cycle Created'),
    ], string="Event", readonly=True)

    amount = fields.Float(
        string="Amount",
        digits=(16, 2),
        readonly=True)

    order_count = fields.Integer(
        string="Sale Orders",
        readonly=True,
        help="Number of sale orders included in this billing event.")

    bill_id = fields.Many2one(
        'account.move', string="Vendor Bill",
        readonly=True, ondelete='set null')

    # Stored separately so history survives bill deletion
    bill_name = fields.Char(
        string="Bill Reference",
        readonly=True)

    user_id = fields.Many2one(
        'res.users', string="Processed By",
        default=lambda self: self.env.user,
        readonly=True)

    note = fields.Char(string="Note", readonly=True)

    currency_id = fields.Many2one(
        'res.currency',
        related='commission_id.currency_id',
        readonly=True)