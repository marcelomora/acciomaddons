# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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


class SaleOrder(osv.osv):
    _inherit = 'sale.order'
    _description = 'Sale Order'
    
    _columns = {
    	'enrollment_id': fields.many2one('ac_enrollment.sale', 'Enrollment', help=''),
    }
    
class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    
    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False, context=None):
        if context is None:
            context = {}
        vals = super(sale_order_line, self)._prepare_order_line_invoice_line(cr, uid, line, account_id, context=context)
        if line.account_analytic_id and not vals['account_analytic_id']:
            vals['account_analytic_id'] = line.account_analytic_id.id
        return vals
    
    _columns = {
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account',
                                               help=''),
    }
     
sale_order_line()    
