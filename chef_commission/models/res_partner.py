from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_chef = fields.Boolean(
        string="Is Chef",
        default=False,
        help="Check this box to mark this partner as a Chef.",
        groups="base.group_system",
    )

    commission_ids = fields.One2many(
        'chef.commission', 'agent_id',
        string="Chef Commissions",
        groups="base.group_system",
    )

    def write(self, vals):
        res = super().write(vals)
        if vals.get('is_chef'):
            for rec in self:
                existing = self.env['chef.commission'].search([
                    ('agent_id', '=', rec.id),
                    ('company_id', '=', self.env.company.id),
                ], limit=1)
                if not existing:
                    self.env['chef.commission'].create({
                        'agent_id': rec.id,
                        'company_id': self.env.company.id,
                    })
        return res

    def action_open_chef_commission(self):
        self.ensure_one()
        # Find existing commission for this company
        commission = self.env['chef.commission'].search([
            ('agent_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)

        # Create one if it doesn't exist
        if not commission:
            commission = self.env['chef.commission'].create({
                'agent_id': self.id,
                'company_id': self.env.company.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Chef Commission',
            'res_model': 'chef.commission',
            'res_id': commission.id,
            'view_mode': 'form',
            'target': 'current',
        }