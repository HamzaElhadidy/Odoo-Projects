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

    # ── Computed: is chef commission enabled for the current company ──
    chef_commission_enabled = fields.Boolean(
        string="Chef Commission Enabled",
        compute='_compute_chef_commission_enabled',
    )

    def _compute_chef_commission_enabled(self):
        enabled = self.env.company.enable_chef_commission
        for rec in self:
            rec.chef_commission_enabled = enabled

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
        commission = self.env['chef.commission'].search([
            ('agent_id', '=', self.id),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
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