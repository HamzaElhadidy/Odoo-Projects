# -*- coding: utf-8 -*-
{
    'name': "Chef Commission",

    'description': """
Chef Commission
    """,

    'author': "Hamza Elhadidy",
    'post_init_hook': 'post_init_hook',

    'category': 'Commission',

    'depends': ['base', 'sale_management','account','mail'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/cron.xml',
        'reports/commission_report_styles.xml',
        'reports/commission_report_template.xml',  
        'reports/commission_report_action.xml',  
        'views/chef_commission_view.xml',
        'views/res_partner_view.xml',
        'views/account_move_view.xml',
        'views/chef_commission_history_view.xml',
        'views/sale_order_view.xml',
        'views/res_config_settings_view.xml',
        'views/res_company_view.xml',
        'views/menu_view.xml',

    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}
