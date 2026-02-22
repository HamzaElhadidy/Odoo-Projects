from odoo import fields, models
from odoo.exceptions import ValidationError

class ChangeStatus(models.TransientModel):
    _name = 'change.status'
    _description = 'Change Property State Wizard'

    property_id = fields.Many2one(
        'real.state',
        string="Property",
        required=True,
        readonly=True
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('rented', 'Rented'),
        ('sold', 'Sold'),
        ('archived', 'Archived'),
    ], string="New Status", required=True)

    reason = fields.Char(
        string="Reason",
        required=True
    )

    def change_status(self):
        self.ensure_one()

        if not self.reason or not self.reason.strip():
            raise ValidationError("You must write a reason for changing the status.")

        self.property_id.change_status_with_reason(
            new_status=self.status,
            reason=self.reason
        )

