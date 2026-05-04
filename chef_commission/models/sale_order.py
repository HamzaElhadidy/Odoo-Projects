from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    chef_id = fields.Many2one(
        'res.partner',
        string="Chef",
        tracking=True,
    )

    chef_commission_enabled = fields.Boolean(
        related='company_id.enable_chef_commission',
        store=False,
    )

    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        # Map each invoice back to its originating order by invoice_origin
        for invoice in invoices:
            if not invoice.invoice_origin:
                continue
            # invoice_origin may be a single order name or comma-separated names
            origin_names = [o.strip() for o in invoice.invoice_origin.split(',')]
            order = self.env['sale.order'].search(
                [('name', 'in', origin_names), ('chef_id', '!=', False)],
                limit=1
            )
            if order and order in self:
                invoice.chef_id = order.chef_id.id

        return invoices