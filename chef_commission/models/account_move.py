from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    chef_id = fields.Many2one(
        'res.partner',
        string="Chef",
    )

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        # Only set chef_id from sale order if not already set by _create_invoices
        for move in moves:
            if move.chef_id:
                continue  # already set by _create_invoices, don't overwrite
            if not move.invoice_origin:
                continue
            origin_names = [o.strip() for o in move.invoice_origin.split(',')]
            order = self.env['sale.order'].search(
                [('name', 'in', origin_names), ('chef_id', '!=', False)],
                limit=1
            )
            if order:
                move.chef_id = order.chef_id.id
        return moves

    def write(self, vals):
        res = super().write(vals)
        if 'payment_state' in vals:
            bills = self.filtered(lambda m: m.move_type == 'in_invoice')
            for bill in bills:
                if bill.payment_state not in ('paid', 'in_payment'):
                    continue
                commissions = self.env['chef.commission'].search([
                    ('invoice_ids', 'in', [bill.id])
                ])
                for commission in commissions:
                    commission._check_bill_payment_status()
        return res

    def js_assign_outstanding_line(self, line_id):
        res = super().js_assign_outstanding_line(line_id)
        self._trigger_vendor_bill_commission_check()
        return res

    def _trigger_vendor_bill_commission_check(self):
        for move in self:
            if move.move_type != 'in_invoice':
                continue
            if move.payment_state not in ('paid', 'in_payment'):
                continue
            commissions = self.env['chef.commission'].search([
                ('invoice_ids', 'in', [move.id])
            ])
            for commission in commissions:
                commission._check_bill_payment_status()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def reconcile(self):
        res = super().reconcile()
        vendor_bills = self.mapped('move_id').filtered(
            lambda m: m.move_type == 'in_invoice'
        )
        for bill in vendor_bills:
            if bill.payment_state not in ('paid', 'in_payment'):
                continue
            commissions = self.env['chef.commission'].search([
                ('invoice_ids', 'in', [bill.id])
            ])
            for commission in commissions:
                commission._check_bill_payment_status()
        return res