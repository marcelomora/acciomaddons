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
{
    'name' : 'Enrollment',
    'version' : '0.1',
    'author' : 'Accioma',
    'category' : 'Educational, Enrollment, Sales',
    'description' : """
Enrollment Sale
==============================
Management of enrollment for student at an educational institute.
    """,
    'website': 'http://www.accioma.com',
    'images' : [],
    'depends' : [
        'base', 
        'sale', 
        'account',
        'onject_merger',
    ],
    'data': [
        'data/ac_enrollment_sequence.xml',
        'op_course/op_course_view.xml',
        'op_standard/op_standard_view.xml',
        'op_batch/op_batch_view.xml',
        'op_subject/op_subject_view.xml',
        'view/enrollment_sale_view.xml',
        'view/student_view.xml',
        'view/invoice_view.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
        'report/report_data.xml',
        'wizard/wizard_print_summary_enrollment.xml'
    ],
    'js': [
    ],
    'qweb' : [
    ],
    'css':[
    ],
    'demo': [
    ],
    'test': [
    ],
    'installable': True,
    'auto_install': False,
}
