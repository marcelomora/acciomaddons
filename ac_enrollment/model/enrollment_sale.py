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

from datetime import datetime, timedelta
import time
from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from openerp import workflow

class enrollment_sale(osv.Model):
    _name = "ac_enrollment.sale"
    _description = "Enrollment"

    _columns = {
        'name':fields.char('Name', 50, required=True, readonly=True),
        'student_id':fields.many2one('ac.student', 'Student', required=True),
        'partner_id':fields.many2one('res.partner', 'Partner'),
 #       'op_standard_id':fields.many2one('op.standard', 'Standard', required=True),
        'enrollment_date':fields.date('Enrollment Date', required=True),
        'enrollment_time':fields.selection([('ordinary', 'Ordinary'),
            ('extraordinay', 'Extraordinary')], string="Enrollment Time"),
        'state':fields.selection([('draft','Draft Enrollment'),
            ('confirmed', 'Confirmed Enrollment'),
            ('paid', 'Paid'),('done', 'Done')], help='fields help'),
        'payment_reference':fields.char('Payment Reference', 255,
            help='Banking deposit or payment reference'),
#        'section':fields.many2one('op.section', 'Section',
#            help='Section of day, accordingly to schedules'),
        'granted':fields.boolean('Granted', help='Is this enrollment granted?'),
        'granted_id':fields.many2one('ac.grant', 'Granted Reference',
            help='Granted Reference'),
        'registration':fields.selection([('ordinary','Ordinary'),
            ('extraordinay', 'Extraordinary')],
            help='Registration type regarding to date'),
        'op_course_id':fields.many2one('op.course', 'Course'),
        'op_standard_id':fields.many2one('op.standard', 'Standard'),
        'op_batch_id':fields.many2one('op.batch', 'Batch'),
        'ac_enrollment_line_ids':fields.one2many('ac_enrollment.sale_line',
            'enrollment_sale_id', 'Lines'),
    }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'ac.enrollment'),
        'enrollment_date': fields.date.today(),
        'enrollment_time': 'ordinary',
        'state':'draft',
    }

    def _create_sale_order(self, cr, uid, enrollment):
        sale_order_obj = self.pool.get('sale.order')
        defaults = sale_order_obj.onchange_partner_id(cr, uid, [],
                enrollment.partner_id.id , context=context)['value']
        defaults['partner_id'] = enrollment.partner_id.id
        customer = enrollment.partner_id
        return sale_order_obj.create(cr, uid, defaults)


    def _create_sale_order_line(self, cr, uid, sale_order_id,
            product_default_code, qty):

        sale_order_obj = self.pool.get('sale.order')
        product_obj = self.pool.get('product.product')
        sale_order_line = self.pool.get('sale.order.line')

        sale_order = sale_order_obj.browse(cr, uid, sale_order_id)

        pricelist = sale_order.pricelist_id
        try:
            product_id = product_obj.search(cr, uid, [
                ('default_code', '=', product_default_code)])[0]
        except:
            return False

        defaults = sale_order_line.product_id_change(cr, uid, [], pricelist.id,
                product_id, qty=qty,
                date_order=fields.date.context_today(self, cr, uid),
                partner_id=sale_order.partner_id.id)['value']

        defaults.update({'order_id':sale_order.id, 'product_id':product_id,
            'product_uom_qty':qty})

        return sale_order_line.create(cr, uid, defaults)


    def action_enrollment_done(self, cr, uid, ids, context=None):
        res = {}

        for enrollment in self.browse(cr, uid, ids, context=context):
            order_id = self._create_sale_order(cr, uid, enrollment)

            enrollment.write({'state':'confirmed'})

        return res



class enrollment_sale_line(osv.Model):
    _name = 'ac_enrollment.sale_line'
    _description = "Enrollment Line"

    def _get_amount(self, cr, uid, ids, field, arg, context=None):
        res = {}

        for line in self.browse(cr, uid, ids, context):
            if line.credits and line.enrollment_price and line.tariff_price:
                res[line.id] = (line.credits * line.enrollment_price) +\
                          (line.credits * line.tariff_price)

            else:
                res[line.id] = 0.0

        return res

    _columns = {
        'enrollment_sale_id':fields.many2one('ac_enrollment.sale', 'Sale',
            required=True, readonly=True),
        'name':fields.char('Description', 255),
        'taken':fields.boolean('Taken'),
        'subject_id':fields.many2one('op.subject', 'Subject'),
        'credits':fields.float('Credits'),
        'enrollment_price':fields.float('Enrollment Price'),
        'tariff_price':fields.float('Tariff Price'),
        'repeat_registration':fields.selection([
            ('first', 'First Registration'),
            ('second', 'Second Registration'),
            ('third', 'Third Registration')],
            help='Number of repeated registrations'),
        'additional_price':fields.float('Additional Price'),
        'amount':fields.function(_get_amount, method=True, store=False,
            fnct_inv=None, fnct_search=None, string='Amount', type='float'),
    }

    def onchange_subject_id(self, cr, uid, ids, subject_id, batch_id, enrollment_time, context=None):
        subject = self.pool.get('op.subject').browse(cr, uid, subject_id, context)
        batch = self.pool.get('op.batch').browse(cr, uid, batch_id, context)
        res = {'value':{'credits': subject.credits, 'enrollment_price': 0.0,
            'tariff_price': 0.0}}
        if enrollment_time == 'ordinary':
            res['value']['enrollment_price'] = batch.or_credit_en_price
            res['value']['tariff_price'] = batch.or_credit_ta_price
        elif enrollment_time == 'extraordinay':
            res['value']['enrollment_price'] = batch.ex_credit_en_price
            res['value']['tariff_price'] = batch.ex_credit_ta_price

        return res


