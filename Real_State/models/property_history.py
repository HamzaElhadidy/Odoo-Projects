from odoo import models, fields , api


class PropertyHistory(models.Model):
    _name = 'property.history'
    _description = 'Property History'
    _order = 'create_date desc'

    user_id = fields.Many2one('res.users', string="Changed By")
    client_name = fields.Many2one('real.state', string="Client Name")
    property_type = fields.Selection(
        related='client_name.property_type',
        store=True,
        readonly=True
    )
    old_state = fields.Char()
    new_state = fields.Char()
    reason = fields.Char()
    create_date = fields.Datetime()


