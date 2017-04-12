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
import time
import re #para busqueda por cedula

from osv import osv, fields
from openerp.tools.translate import _


class ac_student(osv.osv):
    _name = 'ac.student'
    _inherits = {'res.partner':'partner_id'}
    
    def create(self, cr, uid, data, context=None):
        context = context or {}
        existent_partner = []
        partner_obj = self.pool.get('res.partner')
        if 'vat' in data:
            existent_partner = partner_obj.search(cr, uid, [('vat', '=', data.get('vat'))])
            if existent_partner:
                if self.search(cr, uid, [('partner_id', 'in', existent_partner)]):
                    raise osv.except_osv(_('Error!'), _('El estudiante ya existe'))
                data.update(partner_id=existent_partner[0])
                self.pool.get('res.partner').action_open(cr, uid, existent_partner, context=context)
                data.pop('name')
        result = super(ac_student, self).create(cr, uid, data, context=context)
        self.pool.get('res.partner').action_lock(cr, uid, existent_partner, context=context)
        return  result
    
    def correct_res_partner(self, cr, uid, ids, context=None):
        """
        Corrige los estudiantes repetidos y los partner asociados.
        """
        context = context or {}
        ctxt_om = {'active_model': 'ac.student', 'field_to_read': 'to_preserve',
                   'to_invoke': True}
        student_id_repeated, id_repeated = [], []
        repeated_partner, repeated_student = [], []
        id_repeat, student_repeat = False, False
        cr.execute("""select vat
                        from ac_student left join res_partner on
                        partner_id = res_partner.id 
                        group by vat
                        having count(vat) > 1""")
        res = cr.fetchall()
        student_repeated = [id[0] for id in res]
        for student_vat in student_repeated:
            student_repeated = self.search(cr, uid, [('partner_id.vat','=', student_vat)])
            student_repeat = student_repeated[0]
            if len(student_repeated)>1:
                ctxt_om.update(active_ids=student_repeated, 
                               object_to_preserve_id=student_repeated[0])
                self.pool.get('object.merger').action_merge(cr, uid, ids, context=ctxt_om)
                student_repeated.remove(student_repeat)
                repeated_student.extend(student_repeated)
        self.unlink(cr, uid, repeated_student)
        ctxt_om.update(active_model = 'res.partner')
        partner_obj = self.pool.get('res.partner')
        cr.execute("""select vat from res_partner
                        group by vat having count(vat) > 1
                        order by count(vat),vat""")
        res = cr.fetchall()
        vat_repeated = [id[0] for id in res]
        for vat in vat_repeated:
            id_repeated = partner_obj.search(cr, uid, [('vat','=', vat),'|',
                                                       ('active','=',True),('active','=',False)])
            if len(id_repeated)>1:
                id_repeat = [partner_id.id for partner_id in partner_obj.browse(cr,uid,id_repeated) if partner_id.active][0]
                ctxt_om.update(active_ids=id_repeated, object_to_preserve_id=id_repeat)
                self.pool.get('object.merger').action_merge(cr, uid, ids, context=ctxt_om)
                id_repeated.remove(id_repeat)
                repeated_partner.extend(id_repeated)
        partner_obj.unlink(cr, uid, repeated_partner)
        return True
        
    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if 'display_name_compute' in context:
            if context['display_name_compute']:
                return super(ac_student,self).name_get(cr, uid, ids, context=context)
        res = super(ac_student,self).name_get(cr, uid, ids, context=context)
        res2 = []
        if not context.get('show_email'): #evitamos el escneario de formularios de email
            for partner_id, name in res:
                record = self.read(cr, uid, partner_id, ['ref','vat'], context=context)
                new_name = (record['ref'] and '[' + record['ref'] + '] ' or '') + ((record['vat'] and '[' + record['vat'] + '] ' or '')) + name
                res2.append((partner_id, new_name))
            return res2
        return res
    
    def name_search(self, cr, user, name='', args=None, operator='ilike', context=None, limit=100):
        '''
        Permite buscar ya sea por nombre, por codigo o por nombre comercial
        hemos copiado la idea de product.product
        No se llama a super porque name-search no estaba definida
        '''
        if not args:
            args = []
        if not context:
            context = {}
        ids = []
        if name: #no ejecutamos si el usaurio no ha tipeado nada
 
            #buscamos por codigo completo
            ids = self.search(cr, user, ['|',('vat','=',name),('ref','=',name)]+ args, limit=limit, context=context)
            if not ids: #buscamos por fraccion de palabra o fraccion de codigo
                # Do not merge the 2 next lines into one single search, SQL search performance would be abysmal
                # on a database with thousands of matching products, due to the huge merge+unique needed for the
                # OR operator (and given the fact that the 'name' lookup results come from the ir.translation table
                # Performing a quick memory merge of ids in Python will give much better performance
                ids = set()
                ids.update(self.search(cr, user, args + ['|','|',('vat',operator,name),('ref',operator,name),('comercial_name',operator,name)], limit=limit, context=context))
                if not limit or len(ids) < limit:
                    # we may underrun the limit because of dupes in the results, that's fine
                    ids.update(self.search(cr, user, args + [('name',operator,name)], limit=(limit and (limit-len(ids)) or False) , context=context))
                ids = list(ids)
            if not ids:
                ptrn = re.compile('(\[(.*?)\])')
                res = ptrn.search(name)
                if res:
                    ids = self.search(cr, user, ['|','|',('vat','=', res.group(2)),('ref','=', res.group(2)),('comercial_name','=', res.group(2))] + args, limit=limit, context=context)
 
        else: #cuando el usuario no ha escrito nada aun
            ids = self.search(cr, user, args, limit=limit, context=context)
        result = self.name_get(cr, user, ids, context=context)
        return result
    
    _columns = {
        'partner_id': fields.many2one('res.partner', 'Partner',required=True, ondelete="cascade"),
        'grant_id':fields.many2one('ac.grant', 'Grant'),
        'gender': fields.selection([('m','Male'),('f','Female'),('o','Other')], string='Gender', required=True),
        'birth_date':fields.date("Birth Date"),
        'batch_id':fields.many2one('op.batch', 'Last Enrollment Batch',
            help='''The last enrollment batch will be used for calculate the price
            at the enrollment sale view.
            ''', required=False),
    }

    _defaults = {
        'customer': True,
    }
