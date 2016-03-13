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

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'

    _columns = {
        'course_id_id':fields.char('Course', 100, help='Course'),
        'course_description':fields.char('Course Description', 255,
            help='Course Description'),
        'standard_id_id':fields.char('Standard', 255, help='Standard Id'),
        'standard_description':fields.char('Standard Description', 255,
            help='Standard Description'),
        'batch_id_id':fields.char('Batch Id', 100, help='Batch id'),
        'batch_description':fields.char('Batch Description', 255
            , help='Batch Description'),
        'subject_id_id':fields.char('Subject Id', 100, help='Subject Id'),
        'subject_description':fields.char('Subject Description', 255
            , help='Subject description'),
        'hours_id_id':fields.char('Hours id', 100, help='Hours Id'),
        'hours_description':fields.char('Hours Description', 255,
            help='Hours Description'),
        'enrollment_repeat':fields.selection([('1',_('First Enrollment')),
            ('2', _('Second Enrollment')),
            ('3', _('Third Enrollment'))],
            string="Enrollment Number",
            help='Number of repeated enrollments at the same standard'),
        'credits':fields.float('Credits', help='Credits'),
        'is_imported':fields.boolean('Is imported line', help='fields help'),



    }
