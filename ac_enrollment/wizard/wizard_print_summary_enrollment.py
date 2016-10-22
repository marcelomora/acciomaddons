# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (c) 2016 TRESCLOUD Cia Ltda (trescloud.com)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _


class wizard_print_summary_enrollment(osv.osv_memory):
    _name = 'wizard.print.summary.enrollment'
        
    def print_report(self, cr, uid, ids, context=None):
        '''
        Este método se encarga de imprimir el resumen de matrículas
        :param cr: Cursor estándar de base de datos PostgreSQL
        :param uid: ID del usuario actual
        :param ids: IDs del asistente
        :param context: Diccionario de datos de contexto adicional
        '''     
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'report_summary_enrollment',
            'datas': {
                'model': 'wizard.print.summary.enrollment',
                'ids': ids
            }
        }

    _columns = {
        'period_id': fields.many2one('op.batch', 'Period', 
                                     help='This field defines the period to be analyzed in the report')
    }

wizard_print_summary_enrollment()
