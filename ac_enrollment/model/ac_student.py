# -*- coding: utf-8 -*-
#/#############################################################################
#
#    Tech-Receptives Solutions Pvt. Ltd.
#    Copyright (C) 2004-TODAY Tech-Receptives(<http://www.tech-receptives.com>).
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
#/#############################################################################
from osv import osv, fields
import time

class ac_student(osv.osv):
    _name = 'ac.student'
    _inherits = {'res.partner':'partner_id'}

    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner',required=True, ondelete="cascade"),
        'grant_id':fields.many2one('ac.grant', 'Grant'),
        'gender': fields.selection([('m','Male'),('f','Female'),('o','Other')], string='Gender', required=True),
        'birth_date':fields.date("Birth Date"),
        'batch_id':fields.many2one('op.batch', 'Last Enrollment Batch',
            help='''The last enrollment batch will be used for calculate the price
            at the enrollment sale view.
            ''', required=True),



    }

