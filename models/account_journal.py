# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2018 José López <jlopez@indexa.do>

from odoo import models, fields

class AccountJournal(models.Model):
    _inherit = "account.journal"

    show_non_payer_in_report = fields.Boolean("Comprobantes Consumo en Reporte",default=False)
