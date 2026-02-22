# -*- coding: utf-8 -*-
{
    'name': "Real State",

    'description': """
First Project
    """,

    'author': "Hamza Elhadidy",
    'website': "https://www.clientbrief.com",

    'category': 'Project Management',

    'depends': ['base', 'sale_management', 'mail'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'view/base_menu.xml',
        'view/property_history.xml',
        'view/properties.xml',
        'view/property_contract.xml',
        'wizard/change_state_wizard.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'Real_State/static/src/css/client_brief.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
