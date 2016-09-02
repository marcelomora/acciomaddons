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
import openerp
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
    
    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        enrollment = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids, line_ids = [], []
        line_enroll_obj = self.pool.get('ac_enrollment.sale_line')
        for t in enrollment:
            if t['state'] not in ('draft', 'cancel'):
                raise openerp.exceptions.Warning(_('You cannot delete an Enrollment which is not draft or cancelled.'))
            else:
                line_ids.extend([line.id for line in self.browse(cr, uid, t['id'], context=context).ac_enrollment_line_ids])
                unlink_ids.append(t['id'])
        osv.osv.unlink(line_enroll_obj, cr, uid, line_ids, context=context)
        osv.osv.unlink(self, cr, uid, unlink_ids, context=context)
        return True
    
    def copy(self, cr, uid, id, default=None, context=None):
        if not default:
            default = {}
        default.update({
            'sale_order_id': False,
        })
        return super(enrollment_sale, self).copy(cr, uid, id, default, context=context)
    
    def onchange_student_id(self, cr, uid, ids, student_id, context=None):
        context = context or {}
        res = {'value': {}}
        if student_id:
            student = self.pool.get('ac.student').read(cr, uid, student_id, ['partner_id.id'], context=context)
            res['value'].update(partner_id=student.get('partner_id'))
        return res
    
    def onchange_course_date(self, cr, uid, ids, op_course_id, enrollment_date, context=None):
        context = context or {}
        res = {'value': {}, 'domain': {}}
        domain, op_batch_ids, value = [], [], {}
        op_batch_obj = self.pool.get('op.batch')
        if op_course_id and enrollment_date:
            op_batch_ids = op_batch_obj.search(cr, uid, [('course_id','=',op_course_id),
                                                         ('or_en_start_date','<=',enrollment_date),
                                                         ('ex_en_end_date','>=',enrollment_date)], context=context)
        else:
            if op_course_id:
                op_batch_ids = op_batch_obj.search(cr, uid, [('course_id','=',op_course_id)], context=context)
            else:
                op_batch_ids = op_batch_obj.search(cr, uid, [('or_en_start_date','<=',enrollment_date),
                                                             ('ex_en_end_date','>=',enrollment_date)], context=context)
            for op_batch in op_batch_obj.browse(cr, uid, op_batch_ids, context=context):
                enrollment_date_datetime = datetime.strptime(enrollment_date or time.strftime("%Y-%m-%d"), "%Y-%m-%d")
                ordinary_start_date = datetime.strptime(op_batch.or_en_start_date, "%Y-%m-%d")
                ordinary_end_date = datetime.strptime(op_batch.or_en_end_date, "%Y-%m-%d")
                if ordinary_start_date <= enrollment_date_datetime and \
                    enrollment_date_datetime <= ordinary_end_date:
                    value = {'enrollment_time': 'ordinary'}
                extraordinary_start_date = datetime.strptime(op_batch.ex_en_start_date, "%Y-%m-%d")
                extraordinary_end_date = datetime.strptime(op_batch.ex_en_end_date, "%Y-%m-%d")
                if extraordinary_start_date <= enrollment_date_datetime and \
                    enrollment_date_datetime <= extraordinary_end_date:
                    value = {'enrollment_time': 'extraordinary'}
        res['domain'].update(op_batch_id=[('id','in', op_batch_ids)])
        res['value'].update(value)
        return res
    
    def onchange_standard_id(self, cr, uid, ids, op_standard_id, 
                             student_id, enrollment_time, 
                             enrollment_date, context=None):
        context = context or {}
        line_ids = [(5, False, False)]
        op_standard_obj = self.pool.get('op.standard')
        line_obj = self.pool.get('ac_enrollment.sale_line')
        subject_obj = self.pool.get('op.subject')
        res = {'value': {}}
        if op_standard_id and op_standard_id[0] and op_standard_id[0][2]:
            ids = op_standard_id[0][2]
            for level in ids:
                subject_ids = subject_obj.search(cr, uid, [('standard_id', '=', level)])
                for subject in subject_ids:
                    line_id = [0, 0, {
                        'taken': True,
                        'subject_id': subject,
                    }]
                    on_change = line_obj.onchange_subject_id(cr, uid, 
                        [], student_id, level, subject, enrollment_time, 
                        enrollment_date, context=context)
                    line_id[2].update(on_change['value'])
                    line_ids.append(line_id)
        res['value'].update({'ac_enrollment_line_ids': line_ids})
        return res
    
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

    INVOICE_STATE = [
        ('draft','Draft'),
        ('proforma','Pro-forma'),
        ('proforma2','Pro-forma'),
        ('open','Open'),
        ('paid','Paid'),
        ('cancel','Cancelled')
    ]

    _columns = {
        'name':fields.char('Name', 50, required=True, readonly=True),
        'student_id':fields.many2one('ac.student', 'Student', required=True),
        'partner_id':fields.many2one('res.partner', 'Partner', required=True),
        'enrollment_date':fields.date('Enrollment Date', required=True),
        'enrollment_time':fields.selection([('ordinary', 'Ordinary'),
            ('extraordinary', 'Extraordinary')], string="Enrollment Time",
            required=True),
        'state':fields.selection([('draft','Draft Enrollment'),
            ('confirmed', 'Confirmed Enrollment'),
            ('paid', 'Paid'),('done', 'Done')], string="Estado", help='fields help'),
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
        'op_standard_ids':fields.many2many('op.standard', 
                                          'ac_enrollment_sale_op_standard_rel', 'enrollment_id','op_standard_id',
                                          'Standard', required=True),
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
        'account_invoice_id': fields.many2one('account.invoice', 'Account Invoice', 
            help=""""Referenced account invoice to this enrollment"""
            ),
        'school_day':fields.selection([('m','Matutino'),
            ('e', 'Vespertino')], 'Jordada', required=False,
            help='School day assigned to the student'),
        'invoice_state': fields.related('account_invoice_id', 'state', type='selection',
                                        selection=INVOICE_STATE, string='State', readonly=True,
                                        help='This field defines the status of the invoice associated')
    }

    _defaults = {
        'name': lambda obj, cr, uid, context: obj.pool.get('ir.sequence').get(cr, uid, 'ac.enrollment'),
        'enrollment_date': fields.date.today(),
        'enrollment_time': 'ordinary',
        'state':'draft',
    }

    def button_dummy(self, cr, uid, ids, context=None):
        return True

    def write(self, cr, uid, ids, vals, context=None):
        return super(enrollment_sale, self).write(cr, uid, ids, vals, context=context)
    
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
        products.append((enrollment.amount_enrollment, enrollment.op_course_id.enrollment_product_id, u"Matrícula {}".format(enrollment.op_standard_id.name) ))
        products.append((enrollment.amount_tariff, enrollment.op_course_id.tariff_product_id, u"Créditos {}".format(enrollment.op_standard_id.name) ))
        if enrollment.amount_additional:
            products.append((enrollment.amount_additional, enrollment.op_course_id.aditional_product_id, u"Derechos matrícula"))

        for product in products:
            defaults = sale_order_line.product_id_change(cr, uid, [], pricelist.id,
                    product[1].id, qty=1,
                    date_order=fields.date.context_today(self, cr, uid),
                    partner_id=sale_order.partner_id.id)['value']

            defaults.update({'order_id':sale_order.id, 'product_id':product[1].id,
                'product_uom_qty':1, 'price_unit':product[0], 'name': product[2]})

            sale_order_line.create(cr, uid, defaults)

        return True


    def action_enrollment_done(self, cr, uid, ids, context=None):
        res = {}
        for enrollment in self.browse(cr, uid, ids, context=context):
            order_id = self._create_sale_order(cr, uid, enrollment)
            self._create_sale_order_line(cr, uid, order_id, enrollment )
            sale_order_obj = self.pool.get('sale.order')
            sale_order_obj.action_button_confirm(cr, uid, [order_id])
            invoice_id = sale_order_obj.action_invoice_create(cr, uid, [order_id])
            account_invoice_obj = self.pool.get('account.invoice')
            account_invoice_obj.write(cr, uid, [invoice_id], 
                {'student_id': enrollment.student_id.id,
                 'enrollment_id': enrollment.id})
            """
            Link to sale order and account invoice
            """
            enrollment.write({'state':'confirmed', 'sale_order_id': order_id, 'account_invoice_id': invoice_id})
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
            for op_standard_id in enrollment.op_standard_ids:
                subject_ids = subject_obj.search(cr, uid, [('standard_id', '=', op_standard_id.id)])
                if subject_ids:
                    line_obj.unlink(cr, uid, [line.id for line in enrollment.ac_enrollment_line_ids], context)
                for subject in subject_ids:
                    line_id = line_obj.create(cr, uid, {
                        'enrollment_sale_id': enrollment.id,
                        'taken': True,
                        'subject_id': subject,
                    })
                    on_change = line_obj.onchange_subject_id(cr, uid, [line_id], 
                        enrollment.student_id.id, enrollment.op_standard_id.id, subject, 
                        enrollment.enrollment_time, enrollment.enrollment_date, context=None)
    
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

    def onchange_subject_id(self, cr, uid, ids, partner_id, standard_id, 
            subject_id, enrollment_time, date_order, context=None):
        context = context or {}
        result = {}
        if subject_id:
            subject = self.pool.get('op.subject').browse(cr, uid, subject_id, context)
            result = {'credits': subject.credits}
        warning = {}
        domain = {}
        product_uom_obj = self.pool.get('product.uom')
        partner_obj = self.pool.get('res.partner')
        product_obj = self.pool.get('product.product')
        tariff_product, enrollment_product, pricelist = False, False, False
        if standard_id:
            standard = self.pool.get('op.standard').browse(cr, uid, standard_id, context)
            tariff_product =  standard.course_id.tariff_product_id
            enrollment_product = standard.course_id.enrollment_product_id
            additional_product = standard.course_id.aditional_product_id
            if enrollment_time == 'ordinary':
                pricelist = standard.property_product_pricelist
            elif enrollment_time == 'extraordinay':
                pricelist = standard.extra_property_product_pricelist
        products = {'enrollment':enrollment_product, 'tariff': tariff_product,  }
        warning_msgs = ''
        if not pricelist:
            warn_msg = _('You have to select a pricelist standard in the enrollment form !\n'
                    'Please set one before choosing a subject.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            for product_type, product in products.iteritems():
                price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist.id], product.id, subject.credits)[pricelist.id]
                if price is False:
                    warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                            "You have to change either the product, the quantity or the pricelist.")

                    warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
                else:
                    result.update({'%s_price' % product_type: price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        print result
        return {'value': result, 'domain': domain, 'warning': warning}

    def onchange_repeat_registration(self, cr, uid, ids, standard_id, repeat_registration, context=None):
        result = {'additional_price': 0.0 }
        if repeat_registration == 'first':
            return {'value': result}

        standard = self.pool.get('op.standard').browse(cr, uid, standard_id, context)
        product = standard.course_id.aditional_product_id
        pricelist = standard.property_product_pricelist
        result = {}
        warning = {}
        
        warning_msgs = ''


        if not pricelist:
            warn_msg = _('You have to select a pricelist standard in the enrollment form !\n'
                    'Please set one before choosing a subject.')
            warning_msgs += _("No Pricelist ! : ") + warn_msg +"\n\n"
        else:
            price = self.pool.get('product.pricelist').price_get(cr, uid, [pricelist.id], product.id, 1.0)[pricelist.id]

            if price is False:
                warn_msg = _("Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist.")

                warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
            else:
                result.update({'additional_price': price})
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        return {'value': result, 'warning': warning}


