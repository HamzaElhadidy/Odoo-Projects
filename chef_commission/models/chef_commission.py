from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class ChefCommission(models.Model):
    _name = 'chef.commission'
    _description = 'Chef Commission'
    _rec_name = 'agent_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    agent_id = fields.Many2one(
        'res.partner',
        string="Chef",
    )

    # ── Address ──
    street     = fields.Char(related="agent_id.street",    readonly=False)
    street2    = fields.Char(related="agent_id.street2",   readonly=False)
    city       = fields.Char(related="agent_id.city",      readonly=False)
    state_id   = fields.Many2one('res.country.state', related="agent_id.state_id", readonly=False)
    zip        = fields.Char(related="agent_id.zip",       readonly=False)
    country_id = fields.Many2one('res.country', related="agent_id.country_id", readonly=False)

    # ── Contact Info ──
    vat     = fields.Char(related="agent_id.vat",     readonly=False)
    phone   = fields.Char(related="agent_id.phone",   readonly=False)
    mobile  = fields.Char(related="agent_id.mobile",  readonly=False)
    email   = fields.Char(related="agent_id.email",   readonly=False)
    website = fields.Char(related="agent_id.website", readonly=False)
    title   = fields.Many2one('res.partner.title', related="agent_id.title", readonly=False)
    tags    = fields.Many2many('res.partner.category', related='agent_id.category_id')

    today_date = fields.Date(string="Commission Date", default=fields.Date.context_today)
    child_ids  = fields.One2many('res.partner', related='agent_id.child_ids',
                                 string="Contacts & Addresses", readonly=False)

    # ── Sales & Purchase ──
    user_id = fields.Many2one('res.users', related='agent_id.user_id', readonly=False, string="Salesperson")
    team_id = fields.Many2one('crm.team', related='agent_id.team_id', readonly=False, string="Sales Team")
    property_payment_term_id = fields.Many2one(
        'account.payment.term', related='agent_id.property_payment_term_id',
        readonly=False, string="Customer Payment Terms")
    property_supplier_payment_term_id = fields.Many2one(
        'account.payment.term', related='agent_id.property_supplier_payment_term_id',
        readonly=False, string="Vendor Payment Terms")
    property_product_pricelist = fields.Many2one(
        'product.pricelist', related='agent_id.property_product_pricelist',
        readonly=False, string="Pricelist")

    # ── Invoicing ──
    property_account_receivable_id = fields.Many2one(
        'account.account', related='agent_id.property_account_receivable_id',
        readonly=False, string="Account Receivable")
    property_account_payable_id = fields.Many2one(
        'account.account', related='agent_id.property_account_payable_id',
        readonly=False, string="Account Payable")
    property_account_position_id = fields.Many2one(
        'account.fiscal.position', related='agent_id.property_account_position_id',
        readonly=False, string="Fiscal Position")
    bank_ids = fields.One2many(
        'res.partner.bank', related='agent_id.bank_ids',
        string="Bank Accounts", readonly=False)

    # ── Internal Notes ──
    comment = fields.Html(related='agent_id.comment', readonly=False, string="Internal Notes")

    # ── Commission Core ──
    currency_id = fields.Many2one('res.currency', string="Currency",
                                  default=lambda self: self.env.company.currency_id)
    commission_payment_type = fields.Selection([
        ('manually',  'Manually'),
        ('monthly',   'Monthly'),
        ('quarterly', 'Quarterly'),
        ('biyearly',  'Biyearly'),
        ('yearly',    'Yearly'),
    ], string="Commission Payment Type", default='manually')
    next_payment_date = fields.Date(string="Next Payment Date")

    # ── Period tracking ──
    # All fully paid customer invoices with chef_id = this chef AND
    # invoice_date >= period_start_date count toward the current billing cycle.
    period_start_date = fields.Date(
        string="Period Start Date",
        help="Fully paid customer invoices dated on or after this date are included "
             "in the current billing cycle.",
    )

    # ── Percentage-based range lines ──
    commission_line_ids = fields.One2many(
        'chef.commission.line', 'commission_id', string="Commission Ranges")

    company_id = fields.Many2one(
        'res.company', string="Company",
        default=lambda self: self.env.company,
        required=True, index=True)

    state = fields.Selection([
        ('draft',        'Draft'),
        ('confirmed',    'Confirmed'),
        ('bill_created', 'Bill Created'),
        ('paid',         'Paid'),
        ('cancelled',    'Cancelled'),
    ], string="Status", default='draft', tracking=True)

    # ── Vendor bills created for this commission record ──
    invoice_ids = fields.Many2many(
        'account.move', 'agent_commission_invoice_rel',
        'commission_id', 'invoice_id',
        string="Vendor Bills", copy=False)
    invoice_count = fields.Integer(
        string="Bill Count", compute='_compute_invoice_count')

    # ── Live computed commission from period invoices ──
    total_commission = fields.Float(
        string="Total Commission",
        compute='_compute_total_commission',
        store=False,
        digits=(16, 2),
    )

    # ── Sum of all period customer invoices (excl. tax) ──
    period_invoices_total = fields.Float(
        string="Period Invoices Total (excl. tax)",
        compute='_compute_total_commission',
        store=False,
        digits=(16, 2),
    )

    # ── Whether there are fully paid customer invoices not yet billed ──
    has_pending_commission = fields.Boolean(
        string="Has Pending Commission",
        compute='_compute_has_pending',
        store=False,
    )

    # ── History ──
    history_ids = fields.One2many(
        'chef.commission.history', 'commission_id', string="History")

    history_count = fields.Integer(
        string="History Count", compute='_compute_history_count')

    total_paid_amount = fields.Float(
        string="Total Paid",
        compute='_compute_totals_from_history',
        digits=(16, 2),
        store=False)

    total_bills_created = fields.Integer(
        string="Total Bills Created",
        compute='_compute_totals_from_history',
        store=False)

    # ── Add this field to ChefCommission (alongside invoice_ids) ──
    billed_invoice_ids = fields.Many2many(
        'account.move',
        'agent_commission_billed_invoice_rel',
        'commission_id', 'invoice_id',
        string="Already Billed Customer Invoices",
        copy=False,
        help="Customer invoices already included in a previous commission bill. "
            "These are excluded from the current period calculation.",
    )

    # ─────────────────────────────────────────
    # Invoice helpers
    # ─────────────────────────────────────────

    def _get_period_invoices(self):
        """
        Return all fully paid/in_payment posted customer invoices
        whose chef_id = this chef's partner and invoice_date >= period_start_date,
        EXCLUDING invoices already included in a previous commission bill.
        """
        self.ensure_one()
        domain = [
            ('move_type',     '=', 'out_invoice'),
            ('state',         '=', 'posted'),
            ('payment_state', 'in', ('paid', 'in_payment')),
            ('chef_id',       '=', self.agent_id.id),
            # ── Exclude already-billed customer invoices ──
            ('id', 'not in', self.billed_invoice_ids.ids),
        ]
        if self.period_start_date:
            domain.append(('invoice_date', '>=', self.period_start_date))
        return self.env['account.move'].search(domain)

    def _calculate_commission_from_total(self, total):
        """
        Find the matching range and apply its percentage to the grand total.
        Example: total = 250,000 → range 200k-300k at 2% → commission = 5,000
        """
        self.ensure_one()
        for line in self.commission_line_ids:
            if line.from_amount <= total <= line.to_amount:
                return total * (line.percentage / 100.0)
        return 0.0

    def _get_applied_rate(self, total):
        """Return the percentage that matches the given total (for display/logging)."""
        self.ensure_one()
        for line in self.commission_line_ids:
            if line.from_amount <= total <= line.to_amount:
                return line.percentage
        return 0.0

    # ─────────────────────────────────────────
    # Computed
    # ─────────────────────────────────────────

    def _compute_has_pending(self):
        for rec in self:
            if not rec.id or not rec.agent_id:
                rec.has_pending_commission = False
                continue
            rec.has_pending_commission = bool(rec._get_period_invoices())

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.depends('commission_line_ids', 'commission_line_ids.from_amount',
             'commission_line_ids.to_amount', 'commission_line_ids.percentage',
             'period_start_date', 'agent_id')
    def _compute_total_commission(self):
        for rec in self:
            if not rec.id or not rec.agent_id:
                rec.total_commission = 0.0
                rec.period_invoices_total = 0.0
                continue
            invoices = rec._get_period_invoices()
            total = sum(invoices.mapped('amount_untaxed'))
            rec.period_invoices_total = total
            rec.total_commission = rec._calculate_commission_from_total(total)

    @api.depends('history_ids')
    def _compute_history_count(self):
        for rec in self:
            rec.history_count = len(rec.history_ids)

    @api.depends('history_ids.amount', 'history_ids.event')
    def _compute_totals_from_history(self):
        for rec in self:
            paid_lines = rec.history_ids.filtered(
                lambda h: h.event in ('paid', 'auto_payment'))
            rec.total_paid_amount = sum(paid_lines.mapped('amount'))
            rec.total_bills_created = len(rec.history_ids.filtered(
                lambda h: h.event in ('bill_created', 'auto_payment')))
    
    @api.onchange('period_start_date', 'commission_payment_type')
    def _onchange_compute_next_payment_date(self):
        for rec in self:
            if rec.period_start_date and rec.commission_payment_type != 'manually':
                rec.next_payment_date = rec._get_next_payment_date(rec.period_start_date)
            else:
                rec.next_payment_date = False

    # ─────────────────────────────────────────
    # History Helper
    # ─────────────────────────────────────────

    def _log_history(self, event, amount=0.0, invoice_count=0, bill=None, note=''):
        """Create a single history entry for this commission record."""
        self.ensure_one()
        self.env['chef.commission.history'].create({
            'commission_id': self.id,
            'event':         event,
            'amount':        amount,
            'order_count':   invoice_count,
            'bill_id':       bill.id if bill else False,
            'bill_name':     bill.name if bill else '',
            'user_id':       self.env.user.id,
            'note':          note,
        })

    # ─────────────────────────────────────────
    # State Actions
    # ─────────────────────────────────────────

    def action_confirm(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'confirmed'                        # 1. Changes state draft → confirmed
                
                if not rec.period_start_date:                  # 2. If period start not set manually
                    rec.period_start_date = fields.Date.today() #    → set it to today automatically
                
                if rec.commission_payment_type != 'manually':  # 3. If not manual payment type
                    rec.next_payment_date = rec._get_next_payment_date(rec.period_start_date)
                    #    → calculate and set next_payment_date (today + 1 month/quarter/etc.)

    def action_cancel(self):
        for rec in self:
            if rec.state in ('draft', 'confirmed', 'bill_created'):
                rec.state = 'cancelled'
                rec._log_history('cancelled', note="Commission cancelled.")

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state in ('cancelled', 'bill_created'):
                draft_bills = rec.invoice_ids.filtered(lambda m: m.state == 'draft')
                if draft_bills:
                    draft_bills.button_cancel()
                    draft_bills.unlink()

                rec.state = 'draft'
                rec.invoice_ids = [(5, 0, 0)]
                # ── DO NOT touch billed_invoice_ids ──
                rec._log_history('reset', note="Reset to Draft. Bills deleted.")

    def action_new_commission_cycle(self):
        """
        Start a fresh billing cycle.
        Advances period_start_date to today.
        billed_invoice_ids is intentionally kept — it's a permanent exclusion list
        that prevents already-billed invoices from ever being double-counted.
        """
        self.ensure_one()
        today = fields.Date.today()
        self.state = 'draft'
        self.invoice_ids = [(5, 0, 0)]
        self.period_start_date = today
        # ── DO NOT clear billed_invoice_ids here ──
        # It permanently excludes invoices already included in past commission bills.
        # Clearing it would cause double-counting of previously billed invoices.

        self._log_history(
            event='cycle',
            note=f"New cycle started. Period start date set to {today}.",
        )
    # ─────────────────────────────────────────
    # Vendor Bill Creation
    # ─────────────────────────────────────────

    def action_create_bill(self):
        self.ensure_one()

        if not self.agent_id:
            raise UserError("Please set a chef before creating a bill.")
        if self.state != 'confirmed':
            raise UserError("Commission must be confirmed before creating a bill.")

        invoices = self._get_period_invoices()
        if not invoices:
            raise UserError(
                "No fully paid customer invoices found for this chef in the current period.\n\n"
                "Make sure the invoices have the Chef field filled in and are fully paid."
            )

        invoices_total = sum(invoices.mapped('amount_untaxed'))
        total_commission = self._calculate_commission_from_total(invoices_total)
        applied_rate = self._get_applied_rate(invoices_total)

        if total_commission <= 0:
            raise UserError(
                f"Period invoices total (excl. tax): {invoices_total:,.2f}\n\n"
                "No commission range matches this total amount. "
                "Please check the Commission Ranges tab and make sure a range covers this total."
            )

        today = fields.Date.today()
        unique_ref = f"Commission - {self.agent_id.name} - {fields.Datetime.now()}"

        bill_vals = {
            'move_type':      'in_invoice',
            'partner_id':     self.agent_id.id,
            'currency_id':    self.currency_id.id,
            'invoice_origin': self.agent_id.name,
            'invoice_date':   today,
            'ref':            unique_ref,
            'company_id':     self.company_id.id,
            'invoice_line_ids': [(0, 0, {
                'name': (
                    f"Chef Commission — {self.agent_id.name} | "
                    f"Period: {self.period_start_date} → {today} | "
                    f"Invoices total (excl. tax): {invoices_total:,.2f} | "
                    f"Rate: {applied_rate:.2f}%"
                ),
                'quantity':   1,
                'price_unit': total_commission,
            })],
        }
        bill = self.env['account.move'].create(bill_vals)
        self.invoice_ids = [(4, bill.id)]

        # ── Mark these customer invoices as billed so they're excluded next cycle ──
        self.billed_invoice_ids = [(4, inv.id) for inv in invoices]

        self.state = 'bill_created'

        self._log_history(
            event='bill_created',
            amount=total_commission,
            invoice_count=len(invoices),
            bill=bill,
            note=(
                f"Bill created by {self.env.user.name}. "
                f"Period: {self.period_start_date} → {today}. "
                f"Invoices total: {invoices_total:,.2f}. "
                f"Rate: {applied_rate:.2f}%. "
                f"Commission: {total_commission:,.2f}."
            ),
        )

        self.message_post(
            body=(
                f"✅ Vendor bill created: <b>{bill.name}</b><br/>"
                f"Period: {self.period_start_date} → {today}<br/>"
                f"Customer invoices counted: {len(invoices)}<br/>"
                f"Invoices total (excl. tax): {invoices_total:,.2f}<br/>"
                f"Commission rate: {applied_rate:.2f}%<br/>"
                f"Commission amount: <b>{total_commission:,.2f}</b>"
            )
        )

        return {
            'type':      'ir.actions.act_window',
            'name':      'Vendor Bill',
            'res_model': 'account.move',
            'res_id':    bill.id,
            'view_mode': 'form',
            'target':    'current',
        }

    def action_view_bills(self):
        self.ensure_one()
        return {
            'type':      'ir.actions.act_window',
            'name':      'Vendor Bills',
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'domain':    [('id', 'in', self.invoice_ids.ids)],
            'target':    'current',
        }

    # ─────────────────────────────────────────
    # Payment Status
    # ─────────────────────────────────────────

    def _check_bill_payment_status(self):
        for rec in self:
            if rec.state in ('bill_created', 'confirmed') and rec.invoice_ids:
                all_paid = all(
                    inv.payment_state in ('paid', 'in_payment')
                    for inv in rec.invoice_ids
                )
                if all_paid:
                    rec.state = 'paid'
                    rec.message_post(body="All bills fully paid. Commission marked as Paid.")
                    paid_total = sum(inv.amount_total for inv in rec.invoice_ids)
                    rec._log_history(
                        event='paid',
                        amount=paid_total,
                        note="All bills fully paid.",
                    )

                    # ── Auto-reset for scheduler-based commissions ──
                    # If payment type is not manual, automatically start a new cycle
                    # so the scheduler can pick it up again next month/quarter/etc.
                    if rec.commission_payment_type != 'manually':
                        today = fields.Date.today()
                        rec.state = 'confirmed'
                        rec.invoice_ids = [(5, 0, 0)]
                        rec.period_start_date = today
                        # billed_invoice_ids intentionally NOT cleared
                        rec._log_history(
                            event='cycle',
                            note=(
                                f"Auto-cycle started after payment. "
                                f"Next payment: {rec.next_payment_date}."
                            ),
                        )
                        rec.message_post(
                            body=(
                                f"Commission auto-reset to Confirmed for next scheduled cycle.<br/>"
                                f"Next payment date: {rec.next_payment_date}"
                            )
                        )

    def _check_bill_payment_status_all(self):
        records = self.search([('state', '=', 'bill_created')])
        records._check_bill_payment_status()

    # ─────────────────────────────────────────
    # Scheduler
    # ─────────────────────────────────────────

    def _scheduler_auto_payment(self):
        today = fields.Date.today()
        agents = self.search([
            ('state',                                '=',  'confirmed'),
            ('commission_payment_type',              '!=', 'manually'),
            ('next_payment_date',                    '<=', today),
            ('company_id.enable_chef_commission',    '=',  True),   # ← skip disabled companies
        ])
        for agent in agents:
            try:
                invoices = agent._get_period_invoices()
                invoices_total = sum(invoices.mapped('amount_untaxed'))
                total_commission = agent._calculate_commission_from_total(invoices_total)
                applied_rate = agent._get_applied_rate(invoices_total)

                if not invoices or total_commission <= 0:
                    _logger.info(
                        "Scheduler: No commissionable invoices for %s, skipping.",
                        agent.agent_id.name,
                    )
                    agent.next_payment_date = agent._get_next_payment_date(today)
                    continue

                unique_ref = (
                    f"Auto Commission - {agent.agent_id.name} "
                    f"- {fields.Datetime.now()} [ID:{agent.id}]"  # ← now() includes time
                )

                bill_vals = {
                    'move_type':      'in_invoice',
                    'partner_id':     agent.agent_id.id,
                    'currency_id':    agent.currency_id.id,
                    'invoice_origin': agent.agent_id.name,
                    'invoice_date':   today,
                    'ref':            unique_ref,
                    'company_id':     agent.company_id.id,
                    'invoice_line_ids': [(0, 0, {
                        'name': (
                            f"Chef Commission — {agent.agent_id.name} | "
                            f"Period: {agent.period_start_date} → {today} | "
                            f"Invoices total (excl. tax): {invoices_total:,.2f} | "
                            f"Rate: {applied_rate:.2f}%"
                        ),
                        'quantity':   1,
                        'price_unit': total_commission,
                    })],
                }

                bill = self.env['account.move'].create(bill_vals)
                bill.action_post()  # ✅ Post immediately after creation

                # ── Link bill and stamp billed invoices ──
                agent.invoice_ids = [(4, bill.id)]
                agent.billed_invoice_ids = [(4, inv.id) for inv in invoices]

                agent._log_history(
                    event='auto_payment',
                    amount=total_commission,
                    invoice_count=len(invoices),
                    bill=bill,
                    note=(
                        f"Auto-payment on {today}. "
                        f"Invoices total: {invoices_total:,.2f}. "
                        f"Rate: {applied_rate:.2f}%. "
                        f"Commission: {total_commission:,.2f}."
                    ),
                )

                # ── Advance period so next cycle only picks up NEW invoices ──
                agent.next_payment_date = agent._get_next_payment_date(today)
                agent.period_start_date = today

                # ✅ Stay in bill_created — wait for payment before new cycle
                agent.state = 'bill_created'

                agent.message_post(
                    body=(
                        f"Auto-payment triggered on {today}.<br/>"
                        f"Bill: <b>{bill.name}</b><br/>"
                        f"Invoices total (excl. tax): {invoices_total:,.2f}<br/>"
                        f"Commission rate: {applied_rate:.2f}%<br/>"
                        f"Commission amount: <b>{total_commission:,.2f}</b><br/>"
                        f"Next payment date: <b>{agent.next_payment_date}</b>"
                    )
                )

            except Exception as e:
                _logger.exception(
                    "Scheduler error for agent %s on %s", agent.agent_id.name, today
                )
                agent.message_post(body=f"Scheduler error on {today}: {str(e)}")


    def _get_next_payment_date(self, from_date):
        intervals = {
            'monthly':   relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'biyearly':  relativedelta(months=6),
            'yearly':    relativedelta(years=1),
        }
        delta = intervals.get(self.commission_payment_type)
        return from_date + delta if delta else from_date


# ─────────────────────────────────────────────────────────────────────────────
# Range lines — percentage based
# ─────────────────────────────────────────────────────────────────────────────

class AgentCommissionLine(models.Model):
    _name = 'chef.commission.line'
    _description = 'Chef Commission Line'

    commission_id = fields.Many2one('chef.commission', string="Commission", ondelete='cascade')
    from_amount   = fields.Float(string="From Amount",  digits=(16, 2))
    to_amount     = fields.Float(string="To Amount",    digits=(16, 2))
    percentage    = fields.Float(
        string="Commission %",
        digits=(16, 4),
        help="Percentage applied to the total when this range matches. E.g. enter 2 for 2%.",
    )


# ─────────────────────────────────────────────────────────────────────────────
# History Model
# ─────────────────────────────────────────────────────────────────────────────

class ChefCommissionHistory(models.Model):
    _name        = 'chef.commission.history'
    _description = 'Chef Commission History'
    _order       = 'date desc, id desc'

    commission_id = fields.Many2one(
        'chef.commission', string="Commission",
        ondelete='cascade', index=True)

    date = fields.Datetime(
        string="Date", default=fields.Datetime.now, readonly=True)

    event = fields.Selection([
        ('bill_created', 'Bill Created'),
        ('paid',         'Paid'),
        ('auto_payment', 'Auto Payment'),
        ('reset',        'Reset to Draft'),
        ('cancelled',    'Cancelled'),
        ('cycle',        'New Cycle Created'),
    ], string="Event", readonly=True)

    amount = fields.Float(string="Amount", digits=(16, 2), readonly=True)

    order_count = fields.Integer(
        string="Invoices", readonly=True,
        help="Number of customer invoices included in this billing event.")

    bill_id = fields.Many2one(
        'account.move', string="Vendor Bill",
        readonly=True, ondelete='set null')

    bill_name = fields.Char(string="Bill Reference", readonly=True)

    user_id = fields.Many2one(
        'res.users', string="Processed By",
        default=lambda self: self.env.user, readonly=True)

    note = fields.Char(string="Note", readonly=True)

    currency_id = fields.Many2one(
        'res.currency', related='commission_id.currency_id', readonly=True)