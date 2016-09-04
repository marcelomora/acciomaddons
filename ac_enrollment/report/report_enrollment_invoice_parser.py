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

from report import report_sxw
from tools.translate import _


class Parser(report_sxw.rml_parse):
    
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.cr = cr
        self.uid = uid
        self.context = context
        self.localcontext.update({
            'group_by_level_product_subject': lambda invoices: self._group_by_level_product_subject(cr, uid, invoices, context=context)
        })

    def _group_by_level_product_subject(self, cr, uid, invoices, context=None):
        '''
        
        :param cr:
        :param uid:
        :param invoices:
        :param context:
        '''
        if context is None:
            context = {}  
        vals = {}
        account_analytic_ids = []
        standard_obj = self.pool.get('op.standard')
        enrollment_obj = self.pool.get('ac_enrollment.sale')
        enrollment_line_obj = self.pool.get('ac_enrollment.sale_line')
        for invoice in invoices:
            #Verificamos si la factura fue generada mediante una matricula
            enrollment_ids = enrollment_obj.search(cr, uid, [('account_invoice_id','=',invoice.id)], context=context)
            if enrollment_ids:
                for line in invoice.invoice_line:
                    #Obtenemos todos los centros de costo que existen en la factura
                    if line.account_analytic_id and line.account_analytic_id.id not in account_analytic_ids:
                        account_analytic_ids.append(line.account_analytic_id.id)
                #Iteramos por los centros de costo y obtenemos las líneas de factura asociadas a cada uno
                for account_analytic_id in account_analytic_ids:
                    #Obtenemos el nivel asociado al centro de costo
                    level_ids = standard_obj.search(cr, uid, [('account_analytic_id','=',account_analytic_id)], context=context)
                    level = standard_obj.browse(cr, uid, level_ids[0], context=context)
                    vals.setdefault(level.id, [level.name, [], []])     
                    #Guardamos en un diccionario los valores que necesitamos de las líneas de factura que pertencen 
                    #al centro de costo que estamos analizando               
                    for line in invoice.invoice_line:
                        if line.account_analytic_id.id == account_analytic_id:
                            lines = {}
                            lines.update({
                                'code': line.product_id.default_code,
                                'description': line.name,
                                'quantity': line.quantity,
                                'price': line.price_unit,
                                'amount': line.price_subtotal
                            })
                            vals[level.id][1].append(lines)
                    #Buscamos las líneas de matricula que pertencen al nivel asociado al centro de costo
                    enrollment_line_ids = enrollment_line_obj.search(cr, uid, [('enrollment_sale_id','in',enrollment_ids), ('standard_id','in',level_ids)], context=context)
                    #Guardamos en un diccionario los valores que necesitamos de las líneas de matricula
                    for enrollment_line in enrollment_line_obj.browse(cr, uid, enrollment_line_ids, context=context):
                        subjects = {}
                        subjects.update({
                            'subject': enrollment_line.subject_id.name
                        })                        
                        vals[level.id][2].append(subjects)
        return vals    
