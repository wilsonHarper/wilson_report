#  Copyright (c) 2018 - Indexa SRL. (https://www.indexa.do) <info@indexa.do>
#  See LICENSE file for full licensing details.
from werkzeug.utils import redirect
from odoo.http import request, Controller, route

class DgiiReportsControllers(Controller):

    @route(['/l10n_do_dgii_reports/<ncf_rnc>'], type='http', auth='user')
    def redirect_link(self, ncf_rnc):
        env = request.env
        base_url = env['ir.config_parameter'].sudo().get_param('web.base.url')
        if str(ncf_rnc)[:1] == 'B':
            invoice_id = env['account.invoice'].search([('reference', '=', ncf_rnc)], limit=1)
            if invoice_id:
                # Get action depending on invoice type
                action_map = {
                    'out_invoice': request.env.ref('account.action_invoice_tree1'),
                    'in_invoice': request.env.ref('account.action_vendor_bill_template'),
                    'out_refund': request.env.ref('account.action_invoice_out_refund'),
                    'in_refund': request.env.ref('account.action_invoice_in_refund')
                }
                action = action_map[invoice_id.type]
                url = f"{base_url}/web#id={invoice_id.id}&action={action.id}&model=account.invoice&view_type=form"
                return redirect(url)  # Returns invoice form view
            return redirect(base_url)
        else:
            partner_id = env['res.partner'].search([('vat', '=', ncf_rnc)], limit=1)
            if partner_id:
                url = f"{base_url}/web#id={partner_id.id}&model=res.partner&view_type=form" 
                return redirect(url)  # Returns partner form view

            return redirect(base_url)
