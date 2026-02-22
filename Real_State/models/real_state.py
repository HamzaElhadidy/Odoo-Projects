from odoo import models, fields , api
from odoo.exceptions import ValidationError

class ClientBrief(models.Model):
    _name = 'real.state'
    _description = 'Real State'


    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Client Name' ,tracking=True)
    reference = fields.Char(string='Client Reference')
    property_type=  fields.Selection([
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('office', 'Office'),],tracking=True)
    Owner = fields.Char(string='Owner',tracking=True)
    agent = fields.Many2one('res.users', string='Agent',tracking=True, default=lambda self: self.env.user)
    price = fields.Float(string='Price',tracking=True)
    state = fields.Char(string='State')
    history_count = fields.Integer(compute='_compute_history_count',tracking=True)


    status = fields.Selection([
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('rented', 'Rented'),
        ('sold', 'Sold'),
        ('archived', 'Archived'),], default='draft',tracking=True)

    def set_to_draft(self):
        for rec in self:
            rec.status = 'draft'

    def set_to_rented(self):
        for rec in self:
            rec.status = 'rented'

    def set_to_sold(self):
        for rec in self:
            rec.status = 'sold'

    def set_to_reserve(self):
        for rec in self:
            rec.status = 'reserved'

    def set_to_archive(self):
        for rec in self:
            rec.status = 'archived'

    def set_to_available(self):
        for rec in self:
            rec.status = 'available'


    @api.ondelete(at_uninstall=False)
    def _check_delete_allowed(self):
        for rec in self:
            if rec.status not in ['draft', 'reserved', 'available']:
                raise ValidationError(
                    "You can't Delete The Property Unless in Draft Status"
                )


    @api.constrains('agent','status')
    def check_agent(self):
        for rec in self:
            if rec.agent:
                continue
            else:
                if rec.status in ['draft', 'reserved', 'available','archived']:
                    continue
                else:
                    raise ValidationError(
                        "You can't Sell or Rent Any Property Without Agent"
                    )

    def write(self, vals):
        if 'status' in vals:
            for rec in self:
                if rec.status in ('sold', 'archived'):
                    raise ValidationError(
                        "Property Status Can't be Change from Sold or Archived to Another Status"
                    )
        return super(ClientBrief, self).write(vals)

    def change_status_with_reason(self, new_status, reason):
        for rec in self:
            old_status = rec.status

            if not reason or not reason.strip():
                raise ValidationError("Reason is required to change status")

            # business rule
            if rec.status in ('sold', 'archived'):
                raise ValidationError(
                    "Property Status Can't be Change from Sold or Archived"
                )

            # change status
            rec.status = new_status

            # create history ✅ pass old/new status strings, not any other field
            rec.create_property_history(
                old_state=old_status,  # like 'draft'
                new_state=new_status,  # like 'rented'
                reason=reason  # reason text from wizard
            )

    def create_property_history(self, old_state, new_state, reason=""):
        for rec in self:
            self.env['property.history'].create({
                'user_id': self.env.user.id,
                'client_name': rec.id,
                'property_type': rec.property_type,
                'old_state': old_state,
                'new_state': new_state,
                'reason': reason,
            })


    def _compute_history_count(self):
        for rec in self:
            rec.history_count = self.env['property.history'].search_count([
                ('client_name', '=', rec.id)
            ])

    @api.constrains('agent')
    def _check_agent_permissions(self):
        """Prevent agents from changing property agent to someone else"""
        for record in self:
            if self.env.user.has_group('Real_State.property_agent_group') and \
               not self.env.user.has_group('Real_State.property_manager_group'):
                if record.agent != self.env.user:
                    raise ValidationError("Agents can only create/edit their own properties!")