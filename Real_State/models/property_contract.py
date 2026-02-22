from odoo import models, fields, api
from odoo.exceptions import ValidationError


class PropertyContract(models.Model):
    _name = 'property.contract'
    _description = 'Property Contract'

    name = fields.Char(
        string='Contract Reference',
        required=True,
        copy=False
    )

    property_id = fields.Many2one(
        'real.state',
        string='Property',
        required=True
    )

    contract_type = fields.Selection(
        [
            ('sale', 'Sale'),
            ('rent', 'Rent'),
        ],
        required=True
    )

    agent = fields.Char(string='Agent')

    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('closed', 'Closed'),
        ],
        default='draft'
    )

    start_date = fields.Date(required=True)
    end_date = fields.Date()

    active = fields.Boolean(default=True)

    # 🔒 Rules

    @api.constrains('property_id', 'state')
    def _check_one_active_contract(self):
        for rec in self:
            if rec.state == 'active':
                domain = [
                    ('property_id', '=', rec.property_id.id),
                    ('state', '=', 'active'),
                    ('id', '!=', rec.id)
                ]
                if self.search_count(domain):
                    raise ValidationError(
                        'Only one active contract is allowed per property.'
                    )

    @api.constrains('property_id', 'state')
    def _check_property_available(self):
        for rec in self:
            if rec.state == 'active' and rec.property_id.status != 'available':
                raise ValidationError(
                    'You can not activate a contract for a non-available property.'
                )

    # 🔘 Actions

    def action_activate(self):
        for rec in self:
            rec.state = 'active'
            rec.property_id.status = (
                'rented' if rec.contract_type == 'rent' else 'sold'
            )

    def action_close(self):
        for rec in self:
            rec.state = 'closed'

    @api.constrains('property_id')
    def _check_property_access(self):
        """Ensure agents can only create contracts for their own properties"""
        for record in self:
            if self.env.user.has_group('Real_State.property_agent_group') and \
               not self.env.user.has_group('Real_State.property_manager_group'):
                if record.property_id.agent != self.env.user:
                    raise ValidationError("You can only create contracts for your own properties!")