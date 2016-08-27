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
import pdb

class enrollment_sale(osv.Model):
    _name = "ac_enrollment.sale"
    _description = "Enrollment"
    _inherit = "mail.thread"

    def _enrollment_amount(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for enrollment in self.browse(cr, uid, ids, context=context):
            res[enrollment.id] = sum([line.credits * line.enrollment_price
                for line in enrollment.ac_enrollment_line_ids if line.taken])

        return res

    def _tariff_amount(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for enrollment in self.browse(cr, uid, ids, context=context):
            res[enrollment.id] = sum([line.credits * line.tariff_price
                for line in enrollment.ac_enrollment_line_ids if line.taken])

        return res


    def _additional_amount(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for enrollment in self.browse(cr, uid, ids, context=context):
            res[enrollment.id] = sum([line.additional_price
                for line in enrollment.ac_enrollment_line_ids if line.taken])

        return res

    def _total_amount(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for enrollment in self.browse(cr, uid, ids, context=context):
            res[enrollment.id] = enrollment.amount_enrollment + \
                    enrollment.amount_tariff + enrollment.amount_additional
            return res


    _columns = {
        'name':fields.char('Name', 50, required=True, readonly=True),
        'student_id':fields.many2one('ac.student', 'Student', required=True),
        'partner_id':fields.many2one('res.partner', 'Partner', required=True),
        'enrollment_date':fields.date('Enrollment Date', required=True),
        'enrollment_time':fields.selection([('ordinary', 'Ordinary'),
            ('extraordinay', 'Extraordinary')], string="Enrollment Time",
            required=True),
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
            ('extraordinay', 'Extraordinary')], 'Registration', required=False,
            help='Registration type regarding to date'),
        'op_course_id':fields.many2one('op.course', 'Course', required=True),
        'op_standard_id':fields.many2one('op.standard', 'Standard', required=True),
        'op_batch_id':fields.many2one('op.batch', 'Batch', required=True),
        'ac_enrollment_line_ids':fields.one2many('ac_enrollment.sale_line',
            'enrollment_sale_id', 'Lines'),
        'amount_enrollment':fields.function(_enrollment_amount, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Enrollment',
            help='''Enrollment amount'''),
        'amount_tariff':fields.function(_tariff_amount, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Tariff',
            help='''Tariff amount'''),
        'amount_additional':fields.function(_additional_amount, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Additional',
            help='''Tariff amount'''),
        'amount_total':fields.function(_total_amount, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Total',
            help='''Tariff amount'''),
        'sale_order_id': fields.many2one('sale.order', 'Sale Order', 
            help=""""Referenced sale order to this enrollment"""
            ),
        'school_day':fields.selection([('m','Matutino'),
            ('e', 'Vespertino')], 'Jordada', required=False,
            help='School day assigned to the student'),


    }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'ac.enrollment'),
        'enrollment_date': fields.date.today(),
        'enrollment_time': 'ordinary',
        'state':'draft',
    }

    def button_dummy(self, cr, uid, ids, context=None):
        return True


    def _create_sale_order(self, cr, uid, enrollment):
        sale_order_obj = self.pool.get('sale.order')
        defaults = sale_order_obj.onchange_partner_id(cr, uid, [],
                enrollment.partner_id.id)['value']
        defaults['partner_id'] = enrollment.partner_id.id
        defaults['enrollment_id'] = enrollment.id
        customer = enrollment.partner_id

        return sale_order_obj.create(cr, uid, defaults)


    def _create_sale_order_line(self, cr, uid, sale_order_id, enrollment):
        sale_order_obj = self.pool.get('sale.order')
        product_obj = self.pool.get('product.product')
        sale_order_line = self.pool.get('sale.order.line')

        sale_order = sale_order_obj.browse(cr, uid, sale_order_id)

        pricelist = sale_order.pricelist_id
        products = []
        products.append(enrollment.op_course_id.enrollment_product_id)
        products.append(enrollment.op_course_id.tariff_product_id)
        products.append(enrollment.op_course_id.aditional_product_id)

        for product in products:
            defaults = sale_order_line.product_id_change(cr, uid, [], pricelist.id,
                    product.id, qty=1,
                    date_order=fields.date.context_today(self, cr, uid),
                    partner_id=sale_order.partner_id.id)['value']

            defaults.update({'order_id':sale_order.id, 'product_id':product.id,
                'product_uom_qty':1, 'price_unit':0.0})

        return True


    def action_enrollment_done(self, cr, uid, ids, context=None):
        res = {}

        for enrollment in self.browse(cr, uid, ids, context=context):
            order_id = self._create_sale_order(cr, uid, enrollment)
            sale_order_id = self._create_sale_order_line(cr, uid, order_id, enrollment )

            """
            Link to sale order
            """

            enrollment.write({'state':'confirmed', 'sale_order_id': order_id})

        return res

    def action_load_subject(self, cr, uid, ids, context=None):
        """
        Load subject lines
        """
        if not context:
            context = {}

        line_obj = self.pool.get('ac_enrollment.sale_line')
        subject_obj = self.pool.get('op.subject')

        for enrollment in self.browse(cr, uid, ids):
            subject_ids = subject_obj.search(cr, uid, [('standard_id', '=', enrollment.op_standard_id.id)])
            if subject_ids:
                line_obj.unlink(cr, uid, [line.id for line in enrollment.ac_enrollment_line_ids], context)
            for subject in subject_ids:
                line_id = line_obj.create(cr, uid, {
                    'enrollment_sale_id': enrollment.id,
                    'taken': True,
                    'subject_id': subject,
                })
                on_change = line_obj.onchange_subject_id(cr, uid, [line_id], enrollment.student_id.id, 
                    subject, enrollment.op_batch_id, enrollment.enrollment_time, context=None)

                value = on_change['value']
                value['registration'] = 'ordinary'

                line_obj.write(cr, uid, line_id, on_change['value'])

class enrollment_sale_line(osv.Model):
    _name = 'ac_enrollment.sale_line'
    _description = "Enrollment Line"

    def _get_amount(self, cr, uid, ids, field, arg, context=None):
        res = {}

        for line in self.browse(cr, uid, ids, context):
            if line.credits and line.enrollment_price and line.tariff_price:
                res[line.id] = (line.credits * line.enrollment_price) +\
                          (line.credits * line.tariff_price) +\
                          line.additional_price

            else:
                res[line.id] = 0.0

        return res

    _columns = {
        'enrollment_sale_id':fields.many2one('ac_enrollment.sale', 'Sale',
            required=True, readonly=True),
        'name':fields.char('Description', 255),
        'taken':fields.boolean('Taken'),
        'subject_id':fields.many2one('op.subject', 'Subject'),
        'credits':fields.float('Credits', readonly=False),
        'enrollment_price':fields.float('Enrollment Price', readonly=False),
        'tariff_price':fields.float('Tariff Price', readonly=False),
        'repeat_registration':fields.selection([
            ('first', 'First Registration'),
            ('second', 'Second Registration'),
            ('third', 'Third Registration')], 'Repeated Registration',
            help='Number of repeated registrations'),
        'additional_price':fields.float('Additional Price', readonly=False),
        'amount':fields.function(_get_amount, method=True, store=False,
            fnct_inv=None, fnct_search=None, string='Amount', type='float'),
    }

    _defaults = {
        'repeat_registration':'first',
        'taken': True,
    }

    def product_id_change(self, cr, uid, ids, student_id, subject_id, course_id, enrollment_time, context=None):
        if not student_id:
            raise osv.osv_except(_('Error'), _('You must select an student first'))
        student = self.pool.get('ac.student').browse(cr, uid, student_id, context=context)
        subject = self.pool.get('op.subject').browse(cr, uid, subject_id, context)
        course = self.pool.get('op.course').browse(cr, uid, course_id)
        """
        _batch_id = student.batch_id and student.batch_id.id or batch_id
        batch = self.pool.get('op.batch').browse(cr, uid, _batch_id, context)
        res = {'value':{'credits': subject.credits, 'enrollment_price': 0.0,
            'tariff_price': 0.0}}
        if enrollment_time == 'ordinary':
            res['value']['enrollment_price'] = batch.or_credit_en_price
            res['value']['tariff_price'] = batch.or_credit_ta_price
        elif enrollment_time == 'extraordinay':
            res['value']['enrollment_price'] = batch.ex_credit_en_price
            res['value']['tariff_price'] = batch.ex_credit_ta_price
        """

        return res

    def onchange_subject_id(self, cr, uid, ids, standard_id, subject_id, enrollment_time, context=None):
        context = context or {}
        res = {'value':{'credits': subject.credits, 'enrollment_price': 0.0,
            'tariff_price': 0.0}}
        warning = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        standard = self.pool.get('op.standard').browse(cr, uid, standard_id, context)

        #product_obj = product_obj.browse(cr, uid, product, context=context_partner)
        tariff_product = standard.course_id.tariff_product_id
        enrollment_product = standard.course_id.enrollment_product_id
        additional_product = standard.course_id.aditional_product_id
        pricelist = standard.property_product_pricelist
        """
        if not pricelist:
            warn_msg = _('You have to select a pricelist standard in the enrollment form !\n'
                    'Please set one before choosing a subject.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist],
                    product, qty or 1.0, partner_id, {
                        'uom': uom or result.get('product_uom'),
                        'date': date_order,
                        })[pricelist]
            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'price_unit': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'domain': domain, 'warning': warning}
        """
        return {}

    def onchange_repeat_registration(self, cr, uid, ids, student_id,
            subject_id, batch_id, registration_number, context=None):
        if not student_id:
            raise osv.osv_except(('Error'), ('You must select an student first'))
        student = self.pool.get('ac.student').browse(cr, uid, student_id, context=context)
        subject = self.pool.get('op.subject').browse(cr, uid, subject_id, context)
        _batch_id = student.batch_id and student.batch_id.id or batch_id
        batch = self.pool.get('op.batch').browse(cr, uid, _batch_id, context)
        res = {'value':{'additional_price': 0.0 }}
        if registration_number == 'second':
            res['value']['additional_price'] = batch.second_enrollment_price
        elif registration_number == 'third':
            res['value']['additional_price'] = batch.third_enrollment_price

        return res

