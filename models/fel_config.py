from odoo import models, fields, api

class FelConfig(models.Model):
    _name = 'fel.config'
    _description = 'Configuración FEL Guatemala'

    name = fields.Char('Nombre Configuración', required=True)
    company_id = fields.Many2one('res.company', 'Compañía', default=lambda self: self.env.company)
    
    # URLs Servicios
    api_url = fields.Char('URL Certificación', required=True, default='https://certificador.feel.com.gt/fel/certificacion/v2/dte')
    url_anulacion = fields.Char('URL Anulación', required=True, default='https://certificador.feel.com.gt/fel/anulacion/v2/dte')
    sign_url = fields.Char('URL Firma', required=True)
    
    # Credenciales
    infile_sign_key = fields.Char('Llave Firma', required=True)
    infile_sign_user = fields.Char('Usuario Firma', required=True)
    infile_infile_user = fields.Char('Usuario INFILE', required=True)
    infile_infile_key = fields.Char('Llave INFILE', required=True)
    
    # Datos Emisor
    infile_emitter_tax_id = fields.Char('NIT Emisor', required=True)
    infile_emitter_comname = fields.Char('Nombre Comercial', required=True)
    infile_emitter_name = fields.Char('Nombre Legal', required=True)
    infile_emitter_address = fields.Char('Dirección', required=True)
    infile_emitter_zipcode = fields.Char('Código Postal', required=True)
    infile_emitter_city = fields.Char('Municipio', required=True)
    infile_emitter_state = fields.Char('Departamento', required=True)
    infile_emitter_email = fields.Char('Email Emisor', required=True)
    
    # Configuración Adicional
    infile_tax_affilation = fields.Selection([
        ('GEN', 'General'),
        ('PEQ', 'Pequeño Contribuyente')], 
        'Afiliación IVA', default='GEN')
    infile_establishment_id = fields.Char('Código Establecimiento', default='1')
    prefijo_factura = fields.Char('Prefijo Factura', default='FEL')