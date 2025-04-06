{
    'name': 'Facturación Electrónica Guatemala FEL',
    'version': '1.0',
    'external_dependencies': {
    'python': ['xmlsig', 'lxml', 'qrcode']
    },
    'author': 'Tu Nombre',
    'category': 'Accounting',
    'summary': 'Integración con FEL Guatemala a través de INFILE',
    'depends': ['account', 'l10n_gt'],
    'data': [
    'models/fel_config.py',          # Primero modelos
    'models/account_move.py',        # Luego dependencias
    'security/ir.model.access.csv',  # Después seguridad
    'views/fel_config_views.xml',
    'views/account_move_views.xml',
    'data/fel_data.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
