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
from datetime import datetime, timedelta
from trc_mod_python import rounding
import openerp.addons.decimal_precision as dp
import openerp
import time


class enrollment_sale(osv.Model):
    _name = "ac_enrollment.sale"
    _description = "Enrollment"
    _inherit = "mail.thread"
    
    def create(self, cr, uid, vals, context=None):
        '''
        
        :param cr:
        :param uid:
        :param vals:
        :param context:
        '''
        if context is None:
            context = {}
        enrollment_id = super(enrollment_sale, self).create(cr, uid, vals, context=context)
        #Mandamos hacer un write para que se calcule el tree de consolidacón de matricula
        self.write(cr, uid, [enrollment_id], {}, context=context)
        return enrollment_id
    
    def write(self, cr, uid, ids, vals, context=None):
        '''
         
        :param cr:
        :param uid:
        :param ids:
        :param vals:
        :param context:
        '''
        if context is None:
            context = {}
        vals.update({'enrollment_consolidation_ids': self.enrollment_consolidation(cr, uid, ids, context=context)}, context=context)
        return super(enrollment_sale, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param context:
        '''
        if context is None:
            context = {}
        enrollment = self.read(cr, uid, ids, ['state'], context=context)
        unlink_ids, line_ids = [], []
        line_enroll_obj = self.pool.get('ac_enrollment.sale_line')
        for t in enrollment:
            if t['state'] not in ('draft'):
                raise osv.except_osv(_(u'¡Error de Usuario!'), 
                                     _(u'Solamente puede eliminar matrículas en estado borrador.'))
        #=======================================================================
        #     else:
        #         line_ids.extend([line.id for line in self.browse(cr, uid, t['id'], context=context).ac_enrollment_line_ids])
        #         unlink_ids.append(t['id'])
        # osv.osv.unlink(line_enroll_obj, cr, uid, line_ids, context=context)
        #=======================================================================
        osv.osv.unlink(self, cr, uid, ids, context=context)
        return True
    
    def copy(self, cr, uid, id, default=None, context=None):
        '''
        
        :param cr:
        :param uid:
        :param id:
        :param default:
        :param context:
        '''
        if not default:
            default = {}
        default.update({
            'name': '/',
            'sale_order_id': False,
            'account_invoice_id': False
        })
        return super(enrollment_sale, self).copy(cr, uid, id, default, context=context)
    
    def enrollment_consolidation(self, cr, uid, ids, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param context:
        '''
        if context is None:
            context = {}
        level_ids = []
        lines = []
        enrollment_line_obj = self.pool.get('ac_enrollment.sale_line')
        for enrollment in self.browse(cr, uid, ids, context=context):
            #Buscamos cuantos niveles estamos analizando en las líneas de matricula
            level_ids = [line.standard_id.id for line in enrollment.ac_enrollment_line_ids]
            level_ids = list(set(level_ids))
            if level_ids:
                #Para eliminar todas las líneas existentes
                lines.append([5, False, False])
                #Buscamos las líneas para cada nivel
                for level_id in level_ids:
                    amount_enrollment = 0.0
                    amount_tariff = 0.0
                    amount_additional = 0.0
                    line_ids = enrollment_line_obj.search(cr, uid, [('enrollment_sale_id','=',enrollment.id), ('standard_id','=',level_id)], context=context)
                    for line in enrollment_line_obj.browse(cr, uid, line_ids, context=context):
                        amount_enrollment += line.credits * line.enrollment_price
                        amount_tariff += line.credits * line.tariff_price
                        amount_additional += line.additional_price
                    lines.append([0, 0, {'product_id': enrollment.op_course_id.enrollment_product_id.id, 'level': u'Matrícula {}'.format(line.standard_id.name), 'account_analytic_id': line.standard_id.account_analytic_id.id, 'amount': amount_enrollment}])
                    lines.append([0, 0, {'product_id': enrollment.op_course_id.tariff_product_id.id, 'level': u'Créditos {}'.format(line.standard_id.name), 'account_analytic_id': line.standard_id.account_analytic_id.id, 'amount': amount_tariff}])
                    if amount_additional:
                        lines.append([0, 0, {'product_id': enrollment.op_course_id.aditional_product_id.id, 'level':  u'Derechos matrícula {}'.format(line.standard_id.name), 'account_analytic_id': line.standard_id.account_analytic_id.id, 'amount': amount_additional}])
        return lines
    
    def onchange_enrollment_time(self, cr, uid, ids, op_course_id, enrollment_date, 
                                 enrollment_time, op_batch_id, op_standard_ids,
                                 ac_enrollment_line_ids, context=None):
        '''
        
        :param op_course_id:
        :param enrollment_date:
        :param enrollment_time:
        '''
        line_ids = []
        warning = {}
        warn_msg = False
        line_obj = self.pool.get('ac_enrollment.sale_line')
        result = self.onchange_course_date(cr, uid, ids, op_course_id, enrollment_date,
                                           op_batch_id, op_standard_ids, context=context)
        if enrollment_time != result['value'].get('enrollment_time', enrollment_time):
            field = 'enrollment_time'
            context = {'lang': 'es_ES'} if not context else dict(context, lang='es_ES')
            selection = self.fields_get(cr, uid, allfields=[field], context=context)[field]['selection']
            expected, got = '', ''
            for key, value in selection:
                if key == result['value'].get('enrollment_time', enrollment_time):
                    expected = value
                if key == enrollment_time:
                    got = value
            warn_msg = _("Segun la fecha que ha elegido el tipo de matricula es %s pero "
                         "usted esta eligiendo %s. Por favor revise si el tipo de matricula "
                         "es correcto"%(expected, got))
        for opcode, id, values in ac_enrollment_line_ids:
            subject = values.get('subject_id') if values else False
            if opcode == 0:
                line_id = [0, 0, line_obj.onchange_subject_id(cr, uid, ids, False,
                                                              subject, enrollment_time, 
                                                              enrollment_date, context=context).get('value')]
                line_id[2].update({'taken': True,
                                   'subject_id': subject,
                                   'standard_id': values.get('standard_id'),
                                   'repeat_registration': values.get('repeat_registration'),
                                   'additional_price': values.get('additional_price'),
                                   })
                line_ids.append(line_id)
            elif opcode in (1, 4):
                line_browsed_id = line_obj.browse(cr, uid, id, context=context)
                if opcode == 1:
                    subject = subject or line_browsed_id.subject_id.id
                elif opcode == 4:
                    subject = line_browsed_id.subject_id.id
                line_id = [1, id, line_obj.onchange_subject_id(cr, uid, ids, False,
                                                               subject, enrollment_time, 
                                                               enrollment_date, context=context).get('value')]
                line_ids.append(line_id)
        if warn_msg:
            warning={'title': _('Warning!'), 'message': warn_msg}
        return dict(value={'ac_enrollment_line_ids': line_ids}, warning=warning)
    
    def onchange_student_id(self, cr, uid, ids, student_id, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param student_id:
        :param context:
        '''
        context = context or {}
        res = {'value': {}}
        if student_id:
            student = self.pool.get('ac.student').read(cr, uid, student_id, ['partner_id.id'], context=context)
            res['value'].update(partner_id=student.get('partner_id'))
        return res
    
    def onchange_batch_id(self, cr, uid, ids, op_batch_id, enrollment_date, context=None):
        batch_obj = self.pool.get('op.batch')
        res = {'value': {}}
        if enrollment_date and op_batch_id:
            batch_id = batch_obj.browse(cr, uid, op_batch_id, context=context)
            ordinary_start_date = datetime.strptime(batch_id.or_en_start_date, "%Y-%m-%d")
            ordinary_end_date = datetime.strptime(batch_id.or_en_end_date, "%Y-%m-%d")
            extraordinary_start_date = datetime.strptime(batch_id.ex_en_start_date, "%Y-%m-%d")
            extraordinary_end_date = datetime.strptime(batch_id.ex_en_end_date, "%Y-%m-%d")
            enrollment_date = datetime.strptime(enrollment_date, "%Y-%m-%d")
            if ordinary_start_date <= enrollment_date and enrollment_date <= ordinary_end_date:
                res['value'].update({'enrollment_time': 'ordinary'})
            elif extraordinary_start_date <= enrollment_date and enrollment_date <= extraordinary_end_date:
                res['value'].update({'enrollment_time': 'extraordinary'})
            else:
                res['value'].update({'enrollment_time': False})
        return res
        
    def onchange_course_date(self, cr, uid, ids, op_course_id, enrollment_date, 
                             op_batch_id, op_standard_ids, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param op_course_id:
        :param enrollment_date:
        :param context:
        '''
        context = context or {}
        res = {'value': {}, 'domain': {}}
        domain, op_batch_ids, value = [], [], {}
        op_batch_obj = self.pool.get('op.batch')
        if op_course_id and enrollment_date:
            op_batch_ids = op_batch_obj.search(cr, uid, [('course_id','=',op_course_id),
                                                         ('start_date','<=',enrollment_date),
                                                         ('end_date','>=',enrollment_date)], context=context)
        else:
            if op_course_id:
                op_batch_ids = op_batch_obj.search(cr, uid, [('course_id','=',op_course_id)], context=context)
            else:
                op_batch_ids = op_batch_obj.search(cr, uid, [('or_en_start_date','<=',enrollment_date),
                                                             ('ex_en_end_date','>=',enrollment_date)], context=context)
        if op_batch_id:
            if op_batch_obj.browse(cr, uid, op_batch_id, context=context).course_id.id == op_course_id: 
                op_batch_ids = [op_batch_id]
            else:
                batch_ids = op_batch_ids[0] if op_batch_ids else 0
                if not op_course_id:
                    batch_ids = False
                res['value'].update(op_batch_id=batch_ids,op_standard_ids=[[6, 0, []]])
        elif op_batch_ids:
            batch_ids = op_batch_ids[0] if op_batch_ids else 0
            if not op_course_id:
                batch_ids = False
            res['value'].update(op_batch_id=batch_ids,op_standard_ids=[[6, 0, []]])
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
                             enrollment_date, ac_enrollment_line_ids, 
                             context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param op_standard_id:
        :param student_id:
        :param enrollment_time:
        :param enrollment_date:
        :param context:
        '''
        context = context or {}
        line_ids, standard_ids = [], []
        op_standard_obj = self.pool.get('op.standard')
        line_obj = self.pool.get('ac_enrollment.sale_line')
        subject_obj = self.pool.get('op.subject')
        res = {'value': {}}
        updated_levels = []
        for opcode, id, values in ac_enrollment_line_ids:
            level = values.get('standard_id') if values else False
            if opcode == 0:
                updated_levels.append(level)
            elif opcode in (1, 4):
                line_browsed_id = line_obj.browse(cr, uid, id, context=context)
                if opcode == 1:
                    level_id = level or line_browsed_id.standard_id.id
                elif opcode == 4:
                    level_id = line_browsed_id.standard_id.id
                updated_levels.append(level_id)
        if op_standard_id and op_standard_id[0] and op_standard_id[0][2]:
            standard_ids = set(op_standard_id[0][2]) - set(updated_levels)
            for level in standard_ids:
                subject_ids = subject_obj.search(cr, uid, [('standard_id', '=', level)])
                for subject in subject_ids:
                    line_id = [0, 0, {
                        'taken': True,
                        'subject_id': subject,
                        'standard_id': level,
                        'repeat_registration': 'first',
                        'additional_price': 0.0,
                    }]
                    on_change = line_obj.onchange_subject_id(cr, uid, [], student_id, subject, enrollment_time, enrollment_date, context=context)
                    line_id[2].update(on_change['value'])
                    line_ids.append(line_id)
            if not standard_ids:
                standard_ids = set(updated_levels) - set(op_standard_id[0][2])
                remove_subject = []
                for level_remove in standard_ids:
                    for index, (opcode, id, values) in enumerate(ac_enrollment_line_ids):
                        level = values.get('standard_id') if values else False
                        if opcode == 0 and level == level_remove:
                            remove_subject.append([opcode, id, values])
                        elif opcode in (1, 4):
                            line_browsed_id = line_obj.browse(cr, uid, id, context=context)
                            if opcode == 1 and (level == level_remove or \
                                                line_browsed_id.standard_id.id == level_remove):
                                line_id = [2, id, False]
                                line_ids.append(line_id)
                            elif opcode == 4 and line_browsed_id.standard_id.id == level_remove:
                                line_id = [2, id, False]
                                line_ids.append(line_id)
                        elif opcode == 2:
                            line_ids.append([opcode, id, values])
                    for line_index in remove_subject:
                        ac_enrollment_line_ids.remove(line_index)
        if not standard_ids:
            ac_enrollment_line_ids = line_ids = [[5, False, False]]
        line_ids = ac_enrollment_line_ids + line_ids 
        res['value'].update({'ac_enrollment_line_ids': line_ids})
        return res
    
    def action_show_invoice(self, cr, uid, ids, context=None):
        '''        
        Este método muestra las facturas asociadas a la matricula
        :param cr: Cursor estándar de base de datos PostgreSQL
        :param uid: ID del usuario actual
        :param ids: IDs de matricula
        :param context: Diccionario de datos de contexto adicional
        '''
        if context is None:
            context = {}
        sale_obj = self.pool.get('sale.order')
        sale_ids = []
        for enrollment in self.browse(cr, uid, ids, context=context):
            sale_ids.append(enrollment.sale_order_id.id)
        result = sale_obj.action_view_invoice(cr, uid, list(set(sale_ids)), context=context)
        return result
    
    def action_print_report(self, cr, uid, ids, context=None):
        '''
        Este método imprime el reporte de aprobación de becas   
        :param cr: Cursor estándar de base de datos PostgreSQL
        :param uid: ID del usuario actual
        :param ids: IDs de la beca
        :param context: Diccionario de datos de contexto adicional
        '''     
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'report_enrollment',
            'datas': {
                'model': 'ac_enrollment.sale',
                'res_ids': ids
            }
        }

    def _amount_all(self, cr, uid, ids, field, arg, context=None):
        res = {}
        amount_enrollment, amount_tariff, amount_additional, amount_total = [0.0] * 4
        for enrollment in self.browse(cr, uid, ids, context=context): 
            res[enrollment.id] = {'amount_enrollment': 0.0,
                                  'amount_tariff': 0.0,
                                  'amount_additional': 0.0,
                                  'amount_total': 0.0,
                                  }
            for line in enrollment.ac_enrollment_line_ids: 
                if line.taken:
                    amount_enrollment += line.credits * line.enrollment_price
                    amount_tariff += line.credits * line.tariff_price
                    amount_additional += line.additional_price
            amount_total += amount_enrollment + amount_tariff + amount_additional
            res[enrollment.id] = {'amount_enrollment': amount_enrollment,
                                  'amount_tariff': amount_tariff,
                                  'amount_additional': amount_additional,
                                  'amount_total': amount_total,
                                  }
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
        'state':fields.selection([
            ('draft','Draft Enrollment'),
            ('confirmed', 'Confirmed Enrollment'),
            ('cancel', 'Cancelled Enrollment')
        ], "Estado", help='fields help'),
        'payment_reference':fields.char('Payment Reference', 255,
            help='Banking deposit or payment reference'),
        'granted':fields.boolean('Granted', help='Is this enrollment granted?'),
        'granted_id':fields.many2one('ac.grant', 'Granted Reference',
            help='Granted Reference'),
        'registration':fields.selection([('ordinary','Ordinary'),
            ('extraordinary', 'Extraordinary')], 'Registration', required=False,
            help='Registration type regarding to date'),
        'op_course_id':fields.many2one('op.course', 'Course', required=True),
        'op_standard_ids':fields.many2many('op.standard', 
                                          'ac_enrollment_sale_op_standard_rel', 'enrollment_id','op_standard_id',
                                          'Standard', required=True),
        'op_batch_id':fields.many2one('op.batch', 'Batch', required=True),
        'ac_enrollment_line_ids':fields.one2many('ac_enrollment.sale_line',
            'enrollment_sale_id', 'Lines'),
        'amount_enrollment':fields.function(_amount_all, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Enrollment',
            multi="all_enroll", help='''Enrollment amount'''),
        'amount_tariff':fields.function(_amount_all, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Tariff',
            multi="all_enroll", help='''Tariff amount'''),
        'amount_additional':fields.function(_amount_all, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Additional',
            multi="all_enroll", help='''Tariff amount'''),
        'amount_total':fields.function(_amount_all, method=True,
            store=False, fnct_inv=None, fnct_search=None, string='Total',
            multi="all_enroll", help='''Tariff amount'''),
        'sale_order_id': fields.many2one('sale.order', 'Sale Order', 
            help=""""Referenced sale order to this enrollment"""
            ),
        'account_invoice_id': fields.many2one('account.invoice', 'Account Invoice', 
            help=""""Referenced account invoice to this enrollment"""
            ),
        'school_day':fields.selection([('m','Matutino'),
            ('e', 'Vespertino')], 'Jornada', required=False,
            help='School day assigned to the student'),
        'invoice_state': fields.related('account_invoice_id', 'state', type='selection',
                                        selection=INVOICE_STATE, string='State', readonly=True,
                                        help='This field defines the status of the invoice associated'),
        'enrollment_consolidation_ids': fields.one2many('ac.enrollment.consolidation', 'enrollment_consolidation_id', 'Consolidation',
                                                        help=''),
        'user_id': fields.many2one('res.users', 'Done by', 
                                   help=''),
    }

    _defaults = {
        'name': '/',
        'enrollment_date': fields.date.today(),
        'enrollment_time': 'ordinary',
        'state':'draft',
        'user_id': lambda self, cr, uid, context: uid
    }

    def button_dummy(self, cr, uid, ids, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param context:
        '''
        return self.write(cr, uid, ids, {}, context=context)  

    def _create_sale_order(self, cr, uid, enrollment):
        '''
        
        :param cr:
        :param uid:
        :param enrollment:
        '''
        sale_order_obj = self.pool.get('sale.order')
        defaults = sale_order_obj.onchange_partner_id(cr, uid, [],
                enrollment.partner_id.id)['value']
        defaults['partner_id'] = enrollment.partner_id.id
        defaults['enrollment_id'] = enrollment.id
        defaults['user_id'] = uid
        customer = enrollment.partner_id
        return sale_order_obj.create(cr, uid, defaults)

    def _create_sale_order_line(self, cr, uid, sale_order_id, enrollment, context=None):
        '''
        
        :param cr:
        :param uid:
        :param sale_order_id:
        :param enrollment:
        '''
        if context is None:
            context = {}
        invoice_line_ids = []
        enrollment_line_obj = self.pool.get('ac_enrollment.sale_line')
        sale_order_line = self.pool.get('sale.order.line')
        sale_order_obj = self.pool.get('sale.order')
        sale_order = sale_order_obj.browse(cr, uid, sale_order_id, context=context)
        pricelist = sale_order.pricelist_id
        for line in enrollment.enrollment_consolidation_ids:
            defaults = sale_order_line.product_id_change(cr, uid, [], pricelist.id, line.product_id.id, qty=1, 
                                                         date_order=fields.date.context_today(self, cr, uid), 
                                                         partner_id=sale_order.partner_id.id)['value']
            defaults.update({
                'product_id': line.product_id.id,
                'name': line.level,
                'product_uom_qty': 1, 
                'price_unit': line.amount,
                'account_analytic_id': line.account_analytic_id.id,
                'order_id': sale_order.id, 
                'tax_id': [[6, False, defaults.get('tax_id')]]
            })
            order_line_id = sale_order_line.create(cr, uid, defaults, context=context)
            invoice_line_ids.append(order_line_id)              
#             #Para cada producto de los 3 productos a facturar les agregamos las materias que le afectan
#             for line in enrollment.ac_enrollment_line_ids:
#                 line.write({'order_line_ids': [[6, 0, invoice_line_ids]]}) 
#                 line.write({'order_line_ids': [[4, order_line_id]]})
        return True

    def action_enrollment_confirmed(self, cr, uid, ids, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param context:
        '''
        if context is None:
            context = {}
        res = {}
        account_invoice_obj = self.pool.get('account.invoice')
        account_invoice_line_obj = self.pool.get('account.invoice.line')
        for enrollment in self.browse(cr, uid, ids, context=context):
            lines_expected = self.enrollment_consolidation(cr, uid, [enrollment.id], context=context)
            lines_consolidation_expected = {line_expected.get('product_id'): line_expected.get('amount', 0.0) for opcode, id, line_expected in lines_expected if line_expected}
            lines_consolidation_actual = {line.product_id.id: line.amount for line in enrollment.enrollment_consolidation_ids}
            for key in lines_consolidation_expected.keys():
                if key not in lines_consolidation_actual.keys():
                    raise osv.except_osv(_('Error'), _('El resumen de la prefactura es diferente al esperado, por favor, presione el boton \'actualizar\''))
            for line, value in lines_consolidation_expected.iteritems():
                if not rounding.compare_two_floats(value, lines_consolidation_actual.get(line), False, False, '='):
                    raise osv.except_osv(_('Error'), _('El resumen de la prefactura es diferente al esperado, por favor, presione el boton \'actualizar\''))
            order_id = self._create_sale_order(cr, uid, enrollment)
            self._create_sale_order_line(cr, uid, order_id, enrollment, context=context)
            sale_order_obj = self.pool.get('sale.order')
            sale_order_obj.action_button_confirm(cr, uid, [order_id])
            invoice_id = sale_order_obj.action_invoice_create(cr, uid, [order_id], context=context) 
#            invoice_line_ids = account_invoice_line_obj.search(cr, uid, [('invoice_id','=',invoice_id)])
#             #Para cada producto de los 3 productos a facturar les agregamos las materias que le afectan
#             for line in enrollment.ac_enrollment_line_ids:
#                 line.write({'invoice_line_ids': [[6, 0, invoice_line_ids]]})
            #Obtenemos la forma de pago por defecto
            company = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id
            default_payment_id = (enrollment.partner_id.prefer_payment_method and enrollment.partner_id.prefer_payment_method.payment_method_ids and enrollment.partner_id.prefer_payment_method.payment_method_ids[0].id) or (company.prefer_payment_method and company.prefer_payment_method.payment_method_ids and company.prefer_payment_method.payment_method_ids[0].id) or False
            account_invoice_obj.write(cr, uid, [invoice_id], {
                'student_id': enrollment.student_id.id, 
                'enrollment_id': enrollment.id,
                'account_invoice_payment_method_ids': [(0, False, {'payment_id': default_payment_id})]
            })
            account_invoice_obj.button_reset_taxes(cr, uid, [invoice_id], context=context)
            #Se consume la secuencia en el proceso de aprobación. Se guarda el id de la orden de venta y factura asociada en la matricula 
            if enrollment.name == '/':
                name = self.pool.get('ir.sequence').get(cr, uid, 'ac.enrollment')
            else:
                name = enrollment.name
            enrollment.write({'name': name, 'sale_order_id': order_id, 'account_invoice_id': invoice_id, 'state': 'confirmed'})
        return res
    
    def action_enrollment_cancelled(self, cr, uid, ids, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param context:
        '''
        if context is None:
            context = {}
        for enrollment in self.browse(cr, uid, ids, context=context):
            if enrollment.sale_order_id and enrollment.sale_order_id.state != 'cancel':
                raise osv.except_osv(_(u'¡Error de Usuario!'), 
                                     _(u'Para cancelar la matrícula debe anular el pedido de venta %s.')%(enrollment.sale_order_id.name))
            if enrollment.account_invoice_id and enrollment.account_invoice_id.state != 'cancel':
                raise osv.except_osv(_(u'¡Error de Usuario!'), 
                                     _(u'Para cancelar la matrícula debe anular la factura %s.')%(enrollment.account_invoice_id.internal_number))
            self.write(cr, uid, ids, {'state': 'cancel'}, context=context)
        return True
    
    def action_enrollment_draft(self, cr, uid, ids, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param context:
        '''
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        return True               

class enrollment_sale_line(osv.Model):
    _name = 'ac_enrollment.sale_line'
    _description = "Enrollment Line"

    def _get_amount(self, cr, uid, ids, field, arg, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param field:
        :param arg:
        :param context:
        '''
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.credits and line.enrollment_price and line.tariff_price:
                res[line.id] = (line.credits * line.enrollment_price) +\
                          (line.credits * line.tariff_price) +\
                           line.additional_price
            else:
                res[line.id] = 0.0
        return res

    _columns = {
        'enrollment_sale_id':fields.many2one('ac_enrollment.sale', 'Enrollment',
            required=True, readonly=True, ondelete='cascade'),
        'name':fields.char('Description', 255),
        'taken':fields.boolean('Taken'),
        'subject_id':fields.many2one('op.subject', 'Subject'),
        'credits':fields.float('Credits', readonly=False),
        'enrollment_price':fields.float('Enrollment Price', readonly=False),
        'tariff_price':fields.float('Tariff Price', readonly=False),
        'repeat_registration':fields.selection([
            ('first', 'First'),
            ('second', 'Second'),
            ('third', 'Third')], 'Repeated Registration',
            help='Number of repeated registrations'),
        'additional_price':fields.float('Additional Price', readonly=False),
        'amount':fields.function(_get_amount, method=True, store=False,
            fnct_inv=None, fnct_search=None, string='Amount', type='float'),
        'standard_id': fields.many2one('op.standard', 'Level', help=''),
        'order_line_ids':fields.many2many('sale.order.line', 'rel_enrollment_line_order_line', 'enrollment_line_id', 'order_line_id', 
                                          'Order Lines', help=''),
        'invoice_line_ids':fields.many2many('account.invoice.line', 'rel_enrollment_line_invoice_line', 'enrollment_line_id', 'invoice_line_id', 
                                          'Invoice Lines', help=''),
    }

    _defaults = {
        'repeat_registration':'first',
        'taken': True,
    }

    def product_id_change(self, cr, uid, ids, student_id, subject_id, course_id, enrollment_time, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param student_id:
        :param subject_id:
        :param course_id:
        :param enrollment_time:
        :param context:
        '''
        if not student_id:
            raise osv.except_osv(_('Error'), _('You must select an student first'))
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
        elif enrollment_time == 'extraordinary':
            res['value']['enrollment_price'] = batch.ex_credit_en_price
            res['value']['tariff_price'] = batch.ex_credit_ta_price
        """
        return res

    def onchange_subject_id(self, cr, uid, ids, partner_id, subject_id, enrollment_time, date_order, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param partner_id:
        :param standard_id:
        :param subject_id:
        :param enrollment_time:
        :param date_order:
        :param context:
        '''
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
        standard = subject.standard_id
        tariff_product =  standard.course_id.tariff_product_id
        enrollment_product = standard.course_id.enrollment_product_id
        additional_product = standard.course_id.aditional_product_id
        if enrollment_time == 'ordinary':
            pricelist = standard.property_product_pricelist
        elif enrollment_time == 'extraordinary':
            pricelist = standard.extra_property_product_pricelist
        products = {'enrollment':enrollment_product, 'tariff': tariff_product}
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
                result.update(amount=(result.get('credits', 0.0) * result.get('tariff_price', 0.0)) +\
                               (result.get('credits', 0.0) * result.get('enrollment_price', 0.0)) +\
                                result.get('additional_price', 0.0))
        if warning_msgs:
            warning = {
                       'title': _('Configuration Error!'),
                       'message' : warning_msgs
                    }
        print result
        return {'value': result, 'domain': domain, 'warning': warning}

    def onchange_repeat_registration(self, cr, uid, ids, standard_id, repeat_registration, context=None):
        '''
        
        :param cr:
        :param uid:
        :param ids:
        :param standard_id:
        :param repeat_registration:
        :param context:
        '''
        result = {'additional_price': 0.0 }
        if repeat_registration == 'first' or not standard_id:
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


enrollment_sale_line()
    
    
class ac_enrollment_consolidation(osv.osv):
    _name = 'ac.enrollment.consolidation'
    
    _columns = {
        'product_id': fields.many2one('product.product', 'Product', help=''),
        'level': fields.char('Level', help=''),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account',
                                               help=''),
        'amount':fields.float('Amount', digits_compute=dp.get_precision('Account'), help=''),
        'enrollment_consolidation_id': fields.many2one('ac_enrollment.sale', 'Enrollment', required=True, readonly=True,
                                                       ondelete="cascade", help=''),
    }
 
    
ac_enrollment_consolidation()