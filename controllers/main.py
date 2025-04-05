from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)

class FelController(http.Controller):

    @http.route('/fel/get_factura', type='json', auth='user', methods=['POST'])
    def get_factura(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            factura_id = data.get('id')
            move = request.env['account.move'].browse(factura_id)
            return {
                'uuid': move.fel_uuid,
                'serie': move.fel_serie,
                'pdf': move.fel_pdf.decode() if move.fel_pdf else None,
                'status': move.fel_status
            }
        except Exception as e:
            _logger.error("Error obteniendo factura: %s", str(e))
            return {'error': str(e)}

    @http.route('/fel/anular_factura', type='json', auth='user', methods=['POST'])
    def anular_factura(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            factura = request.env['account.move'].browse(data['id'])
            factura.action_fel_anulation()
            return {'status': 'success'}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/fel/generar_pdf/<string:uuid>', type='http', auth='public')
    def generar_pdf_fel(self, uuid, **kwargs):
        factura = request.env['account.move'].sudo().search([('fel_uuid', '=', uuid)], limit=1)
        if factura and factura.fel_pdf:
            return request.make_response(
                base64.b64decode(factura.fel_pdf),
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename={uuid}.pdf')
                ]
            )
        return request.not_found()