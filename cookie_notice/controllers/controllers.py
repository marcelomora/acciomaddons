# -*- coding: utf-8 -*-
from odoo import http

# class CookieNotice(http.Controller):
#     @http.route('/cookie_notice/cookie_notice/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cookie_notice/cookie_notice/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cookie_notice.listing', {
#             'root': '/cookie_notice/cookie_notice',
#             'objects': http.request.env['cookie_notice.cookie_notice'].search([]),
#         })

#     @http.route('/cookie_notice/cookie_notice/objects/<model("cookie_notice.cookie_notice"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cookie_notice.object', {
#             'object': obj
#         })