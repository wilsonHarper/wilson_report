# Part of Domincana Premium.
# See LICENSE file for full copyright and licensing details.
# © 2018 José López <jlopez@indexa.do>

from odoo import models, fields

class ResCompany(models.Model):
    _inherit = "res.company"

    show_non_payer_in_report = fields.Boolean("Comprobantes Consumo en Reporte",default=True)
