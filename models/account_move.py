import logging
import xml.etree.ElementTree as ET
from xml.dom import minidom
import requests
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from lxml import etree

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    fel_uuid = fields.Char('UUID FEL', copy=False, readonly=True)
    fel_serie = fields.Char('Serie FEL', copy=False, readonly=True)
    fel_number = fields.Char('Número FEL', copy=False, readonly=True)
    fel_certification_date = fields.Datetime('Fecha Certificación', readonly=True)
    fel_status = fields.Selection([
        ('draft', 'Borrador'),
        ('pending', 'Pendiente'),
        ('certified', 'Certificado'),
        ('cancelled', 'Anulado'),
        ('error', 'Error')], 
        'Estado FEL', default='draft', tracking=True)
    fel_xml = fields.Binary('XML FEL', attachment=True)
    fel_pdf = fields.Binary('PDF FEL', attachment=True)
    motivo_anulacion = fields.Text('Motivo Anulación')
    identificador_fel = fields.Char('Identificador FEL', copy=False)

    def _get_fel_config(self):
        config = self.env['fel.config'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not config:
            raise UserError(_('Configuración FEL no encontrada!'))
        return config
    
    def _validate_xml_structure(self, xml_content):
        xsd_path = get_module_resource('fel_gt', 'data', 'dte.xsd')  # Archivo XSD oficial
        schema = etree.XMLSchema(etree.parse(xsd_path))
        xml = etree.fromstring(xml_content)
        schema.assertValid(xml)  

    def _get_certificate(self):
        config = self._get_fel_config()
        return {
            'cert_pem': base64.b64decode(config.firma_digital).decode(),
            'key_pem': base64.b64decode(config.llave_privada).decode(),
        }
    def _generate_qr_sat(self):
        base_url = "https://verify.sat.gob.gt/verifyonlinev2/online/consulta"
        return f"{base_url}?ambiente=1&uuid={self.fel_uuid}"
        
    def _generate_fel_xml(self):
        self.ensure_one()
        config = self._get_fel_config()
        
        # Estructura Base
        root = ET.Element('dte:GTDocumento', {
            'xmlns:dte': 'http://www.sat.gob.gt/dte/fel/0.2.0',
            'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
            'Version': '0.1'
        })
        
        # Elemento SAT
        sat = ET.SubElement(root, 'dte:SAT', {'ClaseDocumento': 'dte'})
        dte = ET.SubElement(sat, 'dte:DTE', {'ID': 'DatosCertificados'})
        datos_emision = ET.SubElement(dte, 'dte:DatosEmision', {'ID': 'DatosEmision'})
        
        # Datos Generales
        datos_generales = ET.SubElement(datos_emision, 'dte:DatosGenerales', {
            'CodigoMoneda': 'GTQ',
            'FechaHoraEmision': fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            'Tipo': 'FACT'
        })
        
        # Emisor
        emisor = ET.SubElement(datos_emision, 'dte:Emisor', {
            'AfiliacionIVA': config.infile_tax_affilation,
            'CodigoEstablecimiento': config.infile_establishment_id,
            'CorreoEmisor': config.infile_emitter_email,
            'NITEmisor': config.infile_emitter_tax_id,
            'NombreComercial': config.infile_emitter_comname,
            'NombreEmisor': config.infile_emitter_name
        })
        
        # Dirección Emisor
        direccion_emisor = ET.SubElement(emisor, 'dte:DireccionEmisor')
        ET.SubElement(direccion_emisor, 'dte:Direccion').text = config.infile_emitter_address
        ET.SubElement(direccion_emisor, 'dte:CodigoPostal').text = config.infile_emitter_zipcode
        ET.SubElement(direccion_emisor, 'dte:Municipio').text = config.infile_emitter_city
        ET.SubElement(direccion_emisor, 'dte:Departamento').text = config.infile_emitter_state
        ET.SubElement(direccion_emisor, 'dte:Pais').text = 'GT'
        
        # Receptor
        partner = self.partner_id.commercial_partner_id
        receptor = ET.SubElement(datos_emision, 'dte:Receptor', {
            'CorreoReceptor': partner.email or config.infile_emitter_email,
            'IDReceptor': (partner.vat or '').replace('-', '') or 'CF',
            'NombreReceptor': partner.name
        })
        
        # Dirección Receptor
        direccion_receptor = ET.SubElement(receptor, 'dte:DireccionReceptor')
        ET.SubElement(direccion_receptor, 'dte:Direccion').text = partner.street or 'Ciudad'
        ET.SubElement(direccion_receptor, 'dte:CodigoPostal').text = partner.zip or '01001'
        ET.SubElement(direccion_receptor, 'dte:Municipio').text = partner.city or 'Guatemala'
        ET.SubElement(direccion_receptor, 'dte:Departamento').text = partner.state_id.name or 'Guatemala'
        ET.SubElement(direccion_receptor, 'dte:Pais').text = 'GT'
        
        # Items
        items = ET.SubElement(datos_emision, 'dte:Items')
        for line in self.invoice_line_ids:
            item = ET.SubElement(items, 'dte:Item', {
                'BienOServicio': 'S',
                'NumeroLinea': str(line.sequence)
            })
            ET.SubElement(item, 'dte:Cantidad').text = f"{line.quantity:.6f}"
            ET.SubElement(item, 'dte:UnidadMedida').text = 'UND'
            ET.SubElement(item, 'dte:Descripcion').text = line.name
            ET.SubElement(item, 'dte:PrecioUnitario').text = f"{line.price_unit:.6f}"
            ET.SubElement(item, 'dte:Precio').text = f"{line.price_subtotal:.6f}"
            ET.SubElement(item, 'dte:Descuento').text = '0.00'
            ET.SubElement(item, 'dte:Total').text = f"{line.price_total:.6f}"
        
        # Totales
        totales = ET.SubElement(datos_emision, 'dte:Totales')
        ET.SubElement(totales, 'dte:GranTotal').text = f"{self.amount_total:.6f}"
        
        # Formatear XML
        xml_str = ET.tostring(root, encoding='utf-8')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        return pretty_xml.encode('utf-8')

    def _sign_xml(self, xml_content):
        config = self._get_fel_config()
        try:
            response = requests.post(
                config.sign_url,
                json={
                    'llave': config.infile_sign_key,
                    'archivo': base64.b64encode(xml_content).decode(),
                    'codigo': self.identificador_fel,
                    'alias': config.infile_sign_user,
                    'es_anulacion': 'N'
                },
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            result = response.json()
            if result.get('resultado') != 'true':
                raise UserError(_('Error en firma FEL: %s') % result.get('descripcion'))
            return result['archivo']
        except Exception as e:
            _logger.error("Error signing XML: %s", str(e))
            raise UserError(_('Error al firmar documento: %s') % str(e))

    def _certify_document(self, signed_xml):
        config = self._get_fel_config()
        try:
            response = requests.post(
                config.api_url,
                json={
                    'nit': config.infile_emitter_tax_id,
                    'correo_copia': config.infile_emitter_email,
                    'xml_dte': signed_xml
                },
                headers={
                    'usuario': config.infile_infile_user,
                    'llave': config.infile_infile_key,
                    'identificador': self.identificador_fel,
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            result = response.json()
            if not result.get('resultado'):
                raise UserError(_('Error en certificación FEL: %s') % result.get('descripcion'))
            return result
        except Exception as e:
            _logger.error("Error certifying document: %s", str(e))
            raise UserError(_('Error en certificación: %s') % str(e))

    def action_post(self):
        super().action_post()
        if self.move_type in ['out_invoice', 'out_refund']:
            self._process_fel_certification()

    def _process_fel_certification(self):
        try:
            self.ensure_one()
            config = self._get_fel_config()
            self.identificador_fel = f"{config.prefijo_factura}-{self.id}-{self.company_id.id}"
            
            # Generar XML
            xml_content = self._generate_fel_xml()
            
            # Firmar
            signed_xml = self._sign_xml(xml_content)
            
            # Certificar
            cert_result = self._certify_document(signed_xml)
            
            # Actualizar datos
            self.write({
                'fel_uuid': cert_result.get('uuid'),
                'fel_serie': cert_result.get('serie'),
                'fel_number': cert_result.get('numero'),
                'fel_certification_date': fields.Datetime.now(),
                'fel_status': 'certified',
                'fel_xml': base64.b64encode(xml_content),
                'fel_pdf': base64.b64encode(requests.get(cert_result['pdf']).content)
            })
            
        except Exception as e:
            self.fel_status = 'error'
            _logger.error("FEL Certification Error: %s", str(e))
            raise UserError(_('Error en certificación FEL: %s') % str(e))

    def action_fel_anulation(self):
        self.ensure_one()
        config = self._get_fel_config()
        try:
            # Generar XML Anulación
            root = ET.Element('dte:GTAnulacionDocumento', {
                'xmlns:dte': 'http://www.sat.gob.gt/dte/fel/0.1.0',
                'Version': '0.1'
            })
            
            sat = ET.SubElement(root, 'dte:SAT')
            anulacion = ET.SubElement(sat, 'dte:AnulacionDTE', {'ID': 'DatosCertificados'})
            
            ET.SubElement(anulacion, 'dte:DatosGenerales', {
                'FechaEmisionDocumentoAnular': self.fel_certification_date.strftime('%Y-%m-%dT%H:%M:%S'),
                'FechaHoraAnulacion': fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                'IDReceptor': (self.partner_id.vat or '').replace('-', '') or 'CF',
                'MotivoAnulacion': self.motivo_anulacion,
                'NITEmisor': config.infile_emitter_tax_id,
                'NumeroDocumentoAAnular': self.fel_uuid
            })
            
            xml_content = ET.tostring(root, encoding='utf-8')
            
            # Firmar y enviar anulación
            signed_xml = self._sign_xml(xml_content)
            
            response = requests.post(
                config.url_anulacion,
                json={
                    'nit': config.infile_emitter_tax_id,
                    'correo_copia': config.infile_emitter_email,
                    'xml_base64': signed_xml
                },
                headers={
                    'usuario': config.infile_infile_user,
                    'llave': config.infile_infile_key,
                    'identificador': f"ANUL-{self.fel_uuid}",
                    'Content-Type': 'application/json'
                }
            )
            response.raise_for_status()
            
            if response.json().get('resultado'):
                self.fel_status = 'cancelled'
            else:
                raise UserError(_('Error en anulación: %s') % response.json().get('descripcion'))
                
        except Exception as e:
            _logger.error("FEL Anulation Error: %s", str(e))
            raise UserError(_('Error en anulación: %s') % str(e))
        
    def download_fel_pdf(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/fel/generar_pdf/{self.fel_uuid}',
            'target': 'new'
        }

    def download_fel_xml(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/account.move/{self.id}/fel_xml/{self.fel_uuid}.xml',
            'target': 'new'
        }