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
            'summary_enrollment': lambda period: self._summary_enrollment(cr, uid, period, context=context)
        })

    def _summary_enrollment(self, cr, uid, period, context=None):
        '''
        Este método devuelve un listado de matrículas agrupado por estudiante y filtrado por período
        :param cr: Cursor estándar de base de datos PostgreSQL
        :param uid: ID del usuario actual
        :param period: Período
        :param context: Diccionario de datos de contexto adicional
        '''
        
        def get_name_school_day(self, cr, uid, value, context=None):
            '''
            Este método devuelve un nombre dada una clave, campo jornada de la matrícula
            :param cr: Cursor estándar de base de datos PostgreSQL
            :param uid: ID del usuario actual
            :param value: Valor
            :param context: Diccionario de datos de contexto adicional
            '''
            if context is None:
                context = {}
            name = ''
            if value == 'm':
                name = 'Matutino'
            else:
               name = 'Vespertino'
            return name 
        
        def get_name_repeat_registration(self, cr, uid, value, context=None):
            '''            
            Este método devuelve un nombre dada una clave, campo matrícula repetida de las líneas de matrícula
            :param cr: Cursor estándar de base de datos PostgreSQL
            :param uid: ID del usuario actual
            :param value: Valor
            :param context: Diccionario de datos de contexto adicional
            '''
            if context is None:
                context = {}
            name = ''
            if value == 'first':
                name = 'Primera'
            elif value == 'second':
                name = 'Segunda'
            else:
               name = 'Tercera'
            return name 
        
        def line(self, cr, uid, enrollment_ids, context=None):
            '''
            Este método devuelve las líneas del reporte
            :param cr: Cursor estándar de base de datos PostgreSQL
            :param uid: ID del usuario actual
            :param enrollment_ids: IDs de matrículas
            :param context: Diccionario de datos de contexto adicional
            '''
            if context is None:
                context = {}
            vals = {}
            list_levels = []
            list_school_day = []
            list_repeat_registration = []            
            nro_invoice = ''
            nro_enrollment = ''
            date_enrollment = ''
            levels = ''
            school_day = ''
            enrollments = ''
            for enrollment in self.pool.get('ac_enrollment.sale').browse(cr, uid, enrollment_ids, context=context):
                #Valores constantes
                birth_date = enrollment.student_id.birth_date
                vat = enrollment.student_id.vat
                name = enrollment.student_id.name
                school = enrollment.op_course_id.name
                #Números de factura
                if enrollment.account_invoice_id:
                    if not nro_invoice:
                        nro_invoice += enrollment.account_invoice_id.internal_number
                    else:
                        nro_invoice += '\n' + enrollment.account_invoice_id.internal_number
                #Números de matrícula
                if enrollment.name:
                    if not nro_enrollment:
                        nro_enrollment += enrollment.name
                    else:
                        nro_enrollment += '\n' + enrollment.name
                #Fechas de matrícula
                if enrollment.enrollment_date:
                    if not date_enrollment:
                        date_enrollment += enrollment.enrollment_date
                    else:
                        date_enrollment += '\n' + enrollment.enrollment_date               
                #Niveles    
                for level in enrollment.op_standard_ids:
                    if level.name not in list_levels:
                        list_levels.append(level.name)
                #Jornadas
                for day in enrollment.school_day:
                    if day not in list_school_day:
                        list_school_day.append(day)
                #Matrículas
                for line in enrollment.ac_enrollment_line_ids:
                    if line.repeat_registration not in list_repeat_registration:
                        list_repeat_registration.append(line.repeat_registration)
            #Convetir los niveles a texto             
            for level in list_levels:
                if not levels:
                    levels += level
                else:
                    levels += '\n' + level
            #Convetir las jornadas a texto
            for day in list_school_day:
                if not school_day:
                    school_day += get_name_school_day(self, cr, uid, day, context=context)
                else:
                    school_day += '\n' + get_name_school_day(self, cr, uid, day, context=context)
            #Convetir las matrículas a texto              
            for repeat in list_repeat_registration:
                if not enrollments:
                    enrollments += get_name_repeat_registration(self, cr, uid, repeat, context=context)
                else:
                    enrollments += '\n' + get_name_repeat_registration(self, cr, uid, repeat, context=context)         
            vals.update({
                'nro_invoice': nro_invoice,
                'birth_date': birth_date,
                'vat': vat if vat[:2].upper() != 'EC' else vat[2:],
                'name': name,
                'nro_enrollment': nro_enrollment,
                'date_enrollment': date_enrollment,
                'school': school,
                'levels': levels,
                'school_day': school_day,
                'enrollments': enrollments
            })
            return vals
                
        if context is None:
            context = {}
        summary = {}
        student_ids = []
        summary.setdefault(period.code, [])
        enrollment_obj = self.pool.get('ac_enrollment.sale')     
        enrollment_tmp_ids = enrollment_obj.search(cr, uid, [('op_batch_id','=',period.id)], context=context)
        for enrollment in enrollment_obj.browse(cr, uid, enrollment_tmp_ids, context=context):
            if enrollment.student_id.id not in student_ids:
              student_ids.append(enrollment.student_id.id)
        for student_id in student_ids:
            enrollment_ids = enrollment_obj.search(cr, uid, [('op_batch_id','=',period.id), ('student_id','=',student_id)], context=context)
            vals = line(self, cr, uid, enrollment_ids, context=context)
            summary[period.code].append(vals)
        return summary
    