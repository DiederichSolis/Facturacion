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
        'security/ir.model.access.csv',
        'data/fel_data.xml',
        'views/account_move_views.xml',
        'views/fel_config_views.xml',
        'views/fel_templates.xml'
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
