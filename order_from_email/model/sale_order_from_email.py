# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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
import re
import pdb
import base64
from lxml import etree
from StringIO import StringIO

class sale_from_email(osv.Model):
    _name = 'sale.from.email'
    _description = 'Sale order from email'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _columns = {
        'name':fields.char('Name', 255, help='Name'),
        'state':fields.selection([('draft', 'Draft'), ('done', 'Done')]),
        'email_from':fields.char('From', 255),
    }

    def _create_sale_order(self, cr, uid, partner, context=None):
        sale_order_obj = self.pool.get('sale.order')
        defaults = sale_order_obj.onchange_partner_id(cr, uid, [],
                partner.id, context=context)['value']
        defaults['partner_id'] = partner.id
        return sale_order_obj.create(cr, uid, defaults)

    def _parse_attachment(self, attachment):
        in_rows = False
        items = []
        try:
            xml = base64.b64decode(attachment.datas)
            root = etree.fromstring(xml)
            context = etree.iterparse(StringIO(xml))
        except:
            return []

        for action, elem in context:
            if elem.tag == 'head':
                in_rows = True
                continue

            if in_rows:
                if elem.tag in ('articlenumber', 'quantity'):
                    try:
                        items.append(elem.text)
                    except:
                        pass

            if elem.tag == 'body':
                return dict(items[i:i+2] for i in range(0, len(items), 2))



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

        print defaults

        return sale_order_line.create(cr, uid, defaults)


    def create_orders(self, cr, uid, ids, context=None):
        ir_attachment_obj = self.pool.get('ir.attachment')
        mail_message_obj = self.pool.get('mail.message')
        res_partner_obj = self.pool.get('res.partner')
        mail_ids = mail_message_obj.search(cr, uid,
                [('model', '=', 'sale.from.email'),
                 ('res_id', 'in', ids),
                ])
        for m in mail_message_obj.browse(cr, uid, mail_ids, context=context):
            email_address = re.search(r'[\w.-]+@[\w.-]+', m.email_from).group(0)
            partner_ids = res_partner_obj.search(cr, uid,
                    [('email', '=', email_address)]
                    )

            if not partner_ids:
            #TODO Maybe create a new partner - customer
                return True

            partner = res_partner_obj.browse(cr, uid, partner_ids,
                    context=context)[0]

            sale_order = self._create_sale_order(cr, uid, partner)

            for a in m.attachment_ids:
                for k, v in self._parse_attachment(a).items():
                    self._create_sale_order_line(cr, uid, sale_order, k, int(v))


    _defaults = {
        'name': '/',
        'state': 'draft',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

