# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
import json
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class InvoiceServiceTypeDetail(models.Model):
    _name = 'invoice.service.type.detail'
    _description = "Invoice Service Type Detail"

    name = fields.Char()
    code = fields.Char(size=2)
    parent_code = fields.Char()

    _sql_constraints = [('code_unique', 'unique(code)', _('Code must be unique')),]

class AccountInvoice(models.Model):
    _inherit = 'account.move'

    service_type_detail = fields.Many2one('invoice.service.type.detail')

    service_total_amount = fields.Monetary(compute='_compute_amount_fields', store=True, currency_field='company_currency_id')
    good_total_amount = fields.Monetary(compute='_compute_amount_fields',  store=True, currency_field='company_currency_id')

    payment_date = fields.Date(compute='_compute_taxes_fields', store=True)
    invoiced_itbis = fields.Monetary(compute='_compute_taxes_fields', help='Account fiscal type (A52)',  store=True, currency_field='company_currency_id')
    selective_tax = fields.Monetary(compute='_compute_taxes_fields', help='Account fiscal type (A53)', store=True, currency_field='company_currency_id')
    other_taxes = fields.Monetary(compute='_compute_taxes_fields', help='Account fiscal type (A54)', store=True, currency_field='company_currency_id')
    legal_tip = fields.Monetary(compute='_compute_taxes_fields', help='Account fiscal type (A55)', store=True, currency_field='company_currency_id')
    proportionality_tax = fields.Monetary(compute='_compute_taxes_fields',help= 'Account fiscal type (A29, A30)', store=True, currency_field='company_currency_id')
    cost_itbis = fields.Monetary(compute='_compute_taxes_fields', help='Account fiscal type (A51)', store=True, currency_field='company_currency_id')

    withholded_itbis = fields.Monetary(compute='_compute_withheld_taxes', help='Account fiscal type (A34, A36)',  store=True, currency_field='company_currency_id')
    income_withholding = fields.Monetary(compute='_compute_withheld_taxes', help='Account fiscal type (ISR, A38)', store=True, currency_field='company_currency_id')
    third_withheld_itbis = fields.Monetary(compute='_compute_withheld_taxes', help='Account fiscal type (A34, A36)', store=True, currency_field='company_currency_id')
    third_income_withholding = fields.Monetary(compute='_compute_withheld_taxes', help='Account fiscal type (ISR, A38)', store=True, currency_field='company_currency_id')

    advance_itbis = fields.Monetary(compute='_compute_advance_itbis', store=True, currency_field='company_currency_id')
    isr_withholding_type = fields.Char(compute='_compute_isr_withholding_type', store=True, size=2)
    is_exterior = fields.Boolean(compute='_compute_is_exterior')

    payment_form = fields.Selection([('01', 'Cash'),
                                     ('02', 'Check / Transfer / Deposit'),
                                     ('03', 'Credit Card / Debit Card'),
                                     ('04', 'Credit'), ('05', 'Swap'),
                                     ('06', 'Credit Note'), ('07', 'Mixed')],
                                    compute='_compute_in_invoice_payment_form')
    service_type = fields.Selection([('01', 'Gastos de Personal'),
                                     ('02', 'Gastos por Trabajos, Suministros y Servicios'),
                                     ('03', 'Arrendamientos'), 
                                     ('04', 'Gastos de Activos Fijos'),
                                     ('05', 'Gastos de Representación'), 
                                     ('06', 'Gastos Financieros'),
                                     ('07', 'Gastos de Seguros'),
                                     ('08', 'Gastos por Regalías y otros Intangibles')])
    fiscal_status = fields.Selection([('normal', 'Partial'), 
                                      ('done', 'Reported'), 
                                      ('blocked', 'Not Sent')],
                                    copy=False,
                                    help="* The \'Grey\' status means ...\n"
                                    "* The \'Green\' status means ...\n"
                                    "* The \'Red\' status means ...\n"
                                    "* The blank status means that the invoice have"
                                    "not been included in a report.")
   
    def _convert_to_local_currency(self, amount,calculate_currency = False):
        if not calculate_currency:
            return abs(amount)

        sign = -1 if self.move_type in ['in_refund', 'out_refund'] else 1
        amount = self.currency_id._convert(
            amount, self.company_id.currency_id, self.company_id, self.date
        )
        return abs(amount * sign)

    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id', 'state')
    def _compute_amount_fields(self, reg=None):
        """Compute Purchase amount by product type"""
        invoice = self if reg == None else reg
        for inv in invoice:
            if inv.move_type in ['in_invoice', 'in_refund'] and inv.state != 'draft':
                service_amount = 0
                good_amount = 0
                for line in inv.invoice_line_ids:
                    # Monto calculado en bienes
                    if line.product_id.type in ['product', 'consu']:
                        good_amount += line.price_subtotal
                    # Monto calculado en servicio
                    else:
                        service_amount += line.price_subtotal
                inv.service_total_amount = inv._convert_to_local_currency(service_amount,True)
                inv.good_total_amount = inv._convert_to_local_currency(good_amount,True)

    @api.depends('state')
    def _compute_taxes_fields(self, reg=None):
        """Compute invoice common taxes fields"""
        invoice = self if reg == None else reg
        for inv in invoice:
            if inv.state != 'draft':
                inv.invoiced_itbis = 0
                inv.selective_tax = 0
                inv.other_taxes = 0
                inv.legal_tip = 0
                inv.proportionality_tax = 0
                inv.cost_itbis = 0
                for tax in inv.line_ids:
                    # ITBIS Facturado
                    inv.invoiced_itbis += abs(tax.credit - tax.debit) if tax.account_id.account_fiscal_type == 'A52' else 0
                    # Monto Impuesto Selectivo al Consumo
                    inv.selective_tax += abs(tax.credit - tax.debit) if tax.account_id.account_fiscal_type == 'A53' else 0
                    # Monto Otros Impuestos/Tasas
                    inv.other_taxes += abs(tax.credit - tax.debit) if tax.account_id.account_fiscal_type == 'A54' else 0
                    # Monto Propina Legal
                    inv.legal_tip += abs(tax.credit - tax.debit) if tax.account_id.account_fiscal_type == 'A55' else 0
                    # ITBIS sujeto a proporcionalidad
                    inv.proportionality_tax += abs(tax.credit - tax.debit) if tax.account_id.account_fiscal_type in ('A29','A30') else 0
                    # ITBIS llevado al Costo
                    inv.cost_itbis += abs(tax.credit - tax.debit) if tax.account_id.account_fiscal_type == 'A51' else 0

                #Paymante date
                if inv.payment_state == 'paid':
                    if inv.move_type == 'out_invoice' and any([inv.third_withheld_itbis, inv.third_income_withholding]):
                        payments = inv._get_invoice_payment_widget()
                        inv.payment_date = payments[0]['date'] #Fecha pago

                    if inv.move_type == 'in_invoice' and any([inv.withholded_itbis, inv.income_withholding]):
                        payments = inv._get_invoice_payment_widget()
                        inv.payment_date = payments[0]['date'] #Fecha pago

    @api.depends('state','invoice_payments_widget')
    def _compute_withheld_taxes(self, reg=None):
        invoice = self if reg == None else reg
        for inv in invoice:
            inv.third_withheld_itbis = 0
            inv.third_income_withholding = 0
            if inv.amount_total > inv.amount_residual:
                witheld_itbis_types = ['A34', 'A36']
                witheld_isr_types   = ['ISR', 'A38']

                if inv.move_type == 'in_invoice':
                    inv.withholded_itbis = 0
                    inv.income_withholding = 0
                    for tax in inv.line_ids:
                        # Monto ITBIS Retenido por impuesto COMPRAS
                        inv.withholded_itbis += tax.credit - tax.debit if tax.account_id.account_fiscal_type in witheld_itbis_types else 0
                        # Monto Retención Renta por impuesto COMPRAS
                        inv.income_withholding += tax.credit - tax.debit if tax.account_id.account_fiscal_type in witheld_isr_types else 0

                for payment in inv._get_invoice_payment_widget():
                    if inv.move_type == 'out_invoice':
                        # ITBIS Retenido por Terceros
                        inv.third_withheld_itbis += sum(self._get_payment_move_iterator(payment, inv.move_type, witheld_itbis_types))
                        # Retención de Renta pr Terceros
                        inv.third_income_withholding += sum(self._get_payment_move_iterator(payment, inv.move_type, witheld_isr_types))
                    elif inv.move_type == 'in_invoice':
                        # ITBIS Retenido a Terceros
                        inv.withholded_itbis += sum(self._get_payment_move_iterator(payment, inv.move_type, witheld_itbis_types))
                        # Retención de Renta a Terceros
                        inv.income_withholding += sum(self._get_payment_move_iterator(payment, inv.move_type, witheld_isr_types))

    def _get_invoice_payment_widget(self):
        # j = json.loads(self.invoice_payments_widget)
        j = self.invoice_payments_widget
        return j['content'] if j else []

    @api.depends('invoice_line_ids', 'invoice_line_ids.product_id', 'state')
    def _compute_isr_withholding_type(self, reg=None):
        """Compute ISR Withholding Type
        Keyword / Values:
        01 -- Alquileres
        02 -- Honorarios por Servicios
        03 -- Otras Rentas
        04 -- Rentas Presuntas
        05 -- Intereses Pagados a Personas Jurídicas
        06 -- Intereses Pagados a Personas Físicas
        07 -- Retención por Proveedores del Estado
        08 -- Juegos Telefónicos
        """
        invoice = self if reg == None else reg
        for inv in invoice:
            if inv.move_type == 'in_invoice' and inv.state != 'draft':
                isr = [tax_line.account_id for tax_line in inv.line_ids if tax_line.account_id.account_fiscal_type in ('ISR', 'A38','A34', 'A36')]
                if isr:
                    inv.isr_withholding_type = isr.pop(0).isr_retention_type

    def _get_payment_string(self):
        """Compute Vendor Bills payment method string
        Keyword / Values:
        cash        -- Efectivo
        bank        -- Cheques / Transferencias / Depósitos
        card        -- Tarjeta Crédito / Débito
        credit      -- Compra a Crédito
        swap        -- Permuta
        credit_note -- Notas de Crédito
        mixed       -- Mixto
        """
        payments = []
        p_string = ""

        for payment in self._get_invoice_payment_widget():
            payment_id = self.env['account.payment'].browse(payment['account_payment_id'])
            move_id = False
            if payment_id:
                if payment_id.journal_id.type in ['cash', 'bank']:
                    p_string = payment_id.journal_id.l10n_do_payment_form

            if not payment_id:
                move_id = self.env['account.move'].browse( payment['move_id'])
                if move_id:
                    p_string = 'swap'

            # If invoice is paid, but the payment doesn't come from
            # a journal, assume it is a credit note
            payment = p_string if payment_id or move_id else 'credit_note'
            payments.append(payment)

        methods = {p for p in payments}
        if len(methods) == 1:
            return list(methods)[0]
        elif len(methods) > 1:
            return 'mixed'

    @api.depends('state')
    def _compute_in_invoice_payment_form(self, reg=None):
        invoice = self if reg == None else reg
        for inv in invoice:
            if inv.payment_state == 'paid':
                payment_dict = {'cash': '01', 
                                'bank': '02', 
                                'card': '03',
                                'credit': '04', 
                                'swap': '05',
                                'credit_note': '06', 
                                'mixed': '07'}
                inv.payment_form = payment_dict.get(inv._get_payment_string())
            else:
                inv.payment_form = '04'

    def _get_payment_move_iterator(self, payment, inv_type, witheld_type):
        payment_id = self.env['account.payment'].browse(payment['account_payment_id'])
        if payment_id:
            if inv_type == 'out_invoice':
                return [move_line.debit for move_line in payment_id.move_id.line_ids if move_line.account_id.account_fiscal_type in witheld_type]
            else:
                return [move_line.credit for move_line in payment_id.move_id.line_ids if move_line.account_id.account_fiscal_type in witheld_type]
        else:
            move_id = self.env['account.move'].browse(payment.get('move_id'))
            if move_id:
                if inv_type == 'out_invoice':
                    return [move_line.debit for move_line in move_id.line_ids  if move_line.account_id.account_fiscal_type in witheld_type]
                else:
                    return [move_line.credit for move_line in move_id.line_ids if move_line.account_id.account_fiscal_type in witheld_type]

    @api.depends('invoiced_itbis', 'cost_itbis', 'state')
    def _compute_advance_itbis(self, reg=None):
        invoice = self if reg == None else reg
        for inv in invoice:
            if inv.state != 'draft':
                inv.advance_itbis = inv.invoiced_itbis - inv.cost_itbis

    @api.depends('l10n_do_expense_type')
    def _compute_is_exterior(self, reg=None):
        invoice = self if reg == None else reg
        for inv in invoice:
            inv.is_exterior = True if inv.partner_id.l10n_do_dgii_tax_payer_type == 'foreigner' else False

    @api.onchange('l10n_do_expense_type')
    def onchange_service_type(self):
        self.service_type_detail = False
        return {
            'domain': {
                'service_type_detail': [('parent_code', '=', self.l10n_do_expense_type)]
            }
        }

    @api.onchange('journal_id')
    def ext_onchange_journal_id(self):
        # self.service_type = False
        self.service_type_detail = False

    # @api.model
    def norma_recompute(self):
        """
        This method add all compute fields into []env
        add_todo and then recompute
        all compute fields in case dgii config change and need to recompute.
        :return:
        """
        active_ids = self._context.get("active_ids")
        invoice_ids = self.browse(active_ids)
        # for k, v in self.fields_get().items():
        #     if v.get("store") and v.get("depends"):
        #         self.env.add_to_compute(self._fields[k], invoice_ids)
                # self.env.add_todo(self._fields[k], invoice_ids)

        # self.recompute()
        for inv in invoice_ids:
            self._compute_taxes_fields(inv)
            self._compute_amount_fields(inv)
            self._compute_withheld_taxes(inv)
            self._compute_advance_itbis(inv)
            self._compute_isr_withholding_type(inv)
            self._compute_is_exterior(inv)
            self._compute_in_invoice_payment_form(inv)
