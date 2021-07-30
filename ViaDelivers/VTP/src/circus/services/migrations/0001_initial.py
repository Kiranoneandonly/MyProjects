# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Country',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('country_code', models.CharField(default=False, max_length=3, blank=True, choices=[(b'', b''), (b'AP', b'AP'), (b'EU', b'EU'), (b'AD', b'AD'), (b'AE', b'AE'), (b'AF', b'AF'), (b'AG', b'AG'), (b'AI', b'AI'), (b'AL', b'AL'), (b'AM', b'AM'), (b'AN', b'AN'), (b'AO', b'AO'), (b'AQ', b'AQ'), (b'AR', b'AR'), (b'AS', b'AS'), (b'AT', b'AT'), (b'AU', b'AU'), (b'AW', b'AW'), (b'AZ', b'AZ'), (b'BA', b'BA'), (b'BB', b'BB'), (b'BD', b'BD'), (b'BE', b'BE'), (b'BF', b'BF'), (b'BG', b'BG'), (b'BH', b'BH'), (b'BI', b'BI'), (b'BJ', b'BJ'), (b'BM', b'BM'), (b'BN', b'BN'), (b'BO', b'BO'), (b'BR', b'BR'), (b'BS', b'BS'), (b'BT', b'BT'), (b'BV', b'BV'), (b'BW', b'BW'), (b'BY', b'BY'), (b'BZ', b'BZ'), (b'CA', b'CA'), (b'CC', b'CC'), (b'CD', b'CD'), (b'CF', b'CF'), (b'CG', b'CG'), (b'CH', b'CH'), (b'CI', b'CI'), (b'CK', b'CK'), (b'CL', b'CL'), (b'CM', b'CM'), (b'CN', b'CN'), (b'CO', b'CO'), (b'CR', b'CR'), (b'CU', b'CU'), (b'CV', b'CV'), (b'CX', b'CX'), (b'CY', b'CY'), (b'CZ', b'CZ'), (b'DE', b'DE'), (b'DJ', b'DJ'), (b'DK', b'DK'), (b'DM', b'DM'), (b'DO', b'DO'), (b'DZ', b'DZ'), (b'EC', b'EC'), (b'EE', b'EE'), (b'EG', b'EG'), (b'EH', b'EH'), (b'ER', b'ER'), (b'ES', b'ES'), (b'ET', b'ET'), (b'FI', b'FI'), (b'FJ', b'FJ'), (b'FK', b'FK'), (b'FM', b'FM'), (b'FO', b'FO'), (b'FR', b'FR'), (b'FX', b'FX'), (b'GA', b'GA'), (b'GB', b'GB'), (b'GD', b'GD'), (b'GE', b'GE'), (b'GF', b'GF'), (b'GH', b'GH'), (b'GI', b'GI'), (b'GL', b'GL'), (b'GM', b'GM'), (b'GN', b'GN'), (b'GP', b'GP'), (b'GQ', b'GQ'), (b'GR', b'GR'), (b'GS', b'GS'), (b'GT', b'GT'), (b'GU', b'GU'), (b'GW', b'GW'), (b'GY', b'GY'), (b'HK', b'HK'), (b'HM', b'HM'), (b'HN', b'HN'), (b'HR', b'HR'), (b'HT', b'HT'), (b'HU', b'HU'), (b'ID', b'ID'), (b'IE', b'IE'), (b'IL', b'IL'), (b'IN', b'IN'), (b'IO', b'IO'), (b'IQ', b'IQ'), (b'IR', b'IR'), (b'IS', b'IS'), (b'IT', b'IT'), (b'JM', b'JM'), (b'JO', b'JO'), (b'JP', b'JP'), (b'KE', b'KE'), (b'KG', b'KG'), (b'KH', b'KH'), (b'KI', b'KI'), (b'KM', b'KM'), (b'KN', b'KN'), (b'KP', b'KP'), (b'KR', b'KR'), (b'KW', b'KW'), (b'KY', b'KY'), (b'KZ', b'KZ'), (b'LA', b'LA'), (b'LB', b'LB'), (b'LC', b'LC'), (b'LI', b'LI'), (b'LK', b'LK'), (b'LR', b'LR'), (b'LS', b'LS'), (b'LT', b'LT'), (b'LU', b'LU'), (b'LV', b'LV'), (b'LY', b'LY'), (b'MA', b'MA'), (b'MC', b'MC'), (b'MD', b'MD'), (b'MG', b'MG'), (b'MH', b'MH'), (b'MK', b'MK'), (b'ML', b'ML'), (b'MM', b'MM'), (b'MN', b'MN'), (b'MO', b'MO'), (b'MP', b'MP'), (b'MQ', b'MQ'), (b'MR', b'MR'), (b'MS', b'MS'), (b'MT', b'MT'), (b'MU', b'MU'), (b'MV', b'MV'), (b'MW', b'MW'), (b'MX', b'MX'), (b'MY', b'MY'), (b'MZ', b'MZ'), (b'NA', b'NA'), (b'NC', b'NC'), (b'NE', b'NE'), (b'NF', b'NF'), (b'NG', b'NG'), (b'NI', b'NI'), (b'NL', b'NL'), (b'NO', b'NO'), (b'NP', b'NP'), (b'NR', b'NR'), (b'NU', b'NU'), (b'NZ', b'NZ'), (b'OM', b'OM'), (b'PA', b'PA'), (b'PE', b'PE'), (b'PF', b'PF'), (b'PG', b'PG'), (b'PH', b'PH'), (b'PK', b'PK'), (b'PL', b'PL'), (b'PM', b'PM'), (b'PN', b'PN'), (b'PR', b'PR'), (b'PS', b'PS'), (b'PT', b'PT'), (b'PW', b'PW'), (b'PY', b'PY'), (b'QA', b'QA'), (b'RE', b'RE'), (b'RO', b'RO'), (b'RU', b'RU'), (b'RW', b'RW'), (b'SA', b'SA'), (b'SB', b'SB'), (b'SC', b'SC'), (b'SD', b'SD'), (b'SE', b'SE'), (b'SG', b'SG'), (b'SH', b'SH'), (b'SI', b'SI'), (b'SJ', b'SJ'), (b'SK', b'SK'), (b'SL', b'SL'), (b'SM', b'SM'), (b'SN', b'SN'), (b'SO', b'SO'), (b'SR', b'SR'), (b'ST', b'ST'), (b'SV', b'SV'), (b'SY', b'SY'), (b'SZ', b'SZ'), (b'TC', b'TC'), (b'TD', b'TD'), (b'TF', b'TF'), (b'TG', b'TG'), (b'TH', b'TH'), (b'TJ', b'TJ'), (b'TK', b'TK'), (b'TM', b'TM'), (b'TN', b'TN'), (b'TO', b'TO'), (b'TL', b'TL'), (b'TR', b'TR'), (b'TT', b'TT'), (b'TV', b'TV'), (b'TW', b'TW'), (b'TZ', b'TZ'), (b'UA', b'UA'), (b'UG', b'UG'), (b'UM', b'UM'), (b'US', b'US'), (b'UY', b'UY'), (b'UZ', b'UZ'), (b'VA', b'VA'), (b'VC', b'VC'), (b'VE', b'VE'), (b'VG', b'VG'), (b'VI', b'VI'), (b'VN', b'VN'), (b'VU', b'VU'), (b'WF', b'WF'), (b'WS', b'WS'), (b'YE', b'YE'), (b'YT', b'YT'), (b'RS', b'RS'), (b'ZA', b'ZA'), (b'ZM', b'ZM'), (b'ME', b'ME'), (b'ZW', b'ZW'), (b'A1', b'A1'), (b'A2', b'A2'), (b'O1', b'O1'), (b'AX', b'AX'), (b'GG', b'GG'), (b'IM', b'IM'), (b'JE', b'JE'), (b'BL', b'BL'), (b'MF', b'MF'), (b'BQ', b'BQ'), (b'SS', b'SS')])),
                ('country_name', models.CharField(default=False, max_length=70, blank=True, choices=[(b'', b''), (b'Asia/Pacific Region', b'Asia/Pacific Region'), (b'Europe', b'Europe'), (b'Andorra', b'Andorra'), (b'United Arab Emirates', b'United Arab Emirates'), (b'Afghanistan', b'Afghanistan'), (b'Antigua and Barbuda', b'Antigua and Barbuda'), (b'Anguilla', b'Anguilla'), (b'Albania', b'Albania'), (b'Armenia', b'Armenia'), (b'Netherlands Antilles', b'Netherlands Antilles'), (b'Angola', b'Angola'), (b'Antarctica', b'Antarctica'), (b'Argentina', b'Argentina'), (b'American Samoa', b'American Samoa'), (b'Austria', b'Austria'), (b'Australia', b'Australia'), (b'Aruba', b'Aruba'), (b'Azerbaijan', b'Azerbaijan'), (b'Bosnia and Herzegovina', b'Bosnia and Herzegovina'), (b'Barbados', b'Barbados'), (b'Bangladesh', b'Bangladesh'), (b'Belgium', b'Belgium'), (b'Burkina Faso', b'Burkina Faso'), (b'Bulgaria', b'Bulgaria'), (b'Bahrain', b'Bahrain'), (b'Burundi', b'Burundi'), (b'Benin', b'Benin'), (b'Bermuda', b'Bermuda'), (b'Brunei Darussalam', b'Brunei Darussalam'), (b'Bolivia', b'Bolivia'), (b'Brazil', b'Brazil'), (b'Bahamas', b'Bahamas'), (b'Bhutan', b'Bhutan'), (b'Bouvet Island', b'Bouvet Island'), (b'Botswana', b'Botswana'), (b'Belarus', b'Belarus'), (b'Belize', b'Belize'), (b'Canada', b'Canada'), (b'Cocos (Keeling) Islands', b'Cocos (Keeling) Islands'), (b'Congo, The Democratic Republic of the', b'Congo, The Democratic Republic of the'), (b'Central African Republic', b'Central African Republic'), (b'Congo', b'Congo'), (b'Switzerland', b'Switzerland'), (b"Cote D'Ivoire", b"Cote D'Ivoire"), (b'Cook Islands', b'Cook Islands'), (b'Chile', b'Chile'), (b'Cameroon', b'Cameroon'), (b'China', b'China'), (b'Colombia', b'Colombia'), (b'Costa Rica', b'Costa Rica'), (b'Cuba', b'Cuba'), (b'Cape Verde', b'Cape Verde'), (b'Christmas Island', b'Christmas Island'), (b'Cyprus', b'Cyprus'), (b'Czech Republic', b'Czech Republic'), (b'Germany', b'Germany'), (b'Djibouti', b'Djibouti'), (b'Denmark', b'Denmark'), (b'Dominica', b'Dominica'), (b'Dominican Republic', b'Dominican Republic'), (b'Algeria', b'Algeria'), (b'Ecuador', b'Ecuador'), (b'Estonia', b'Estonia'), (b'Egypt', b'Egypt'), (b'Western Sahara', b'Western Sahara'), (b'Eritrea', b'Eritrea'), (b'Spain', b'Spain'), (b'Ethiopia', b'Ethiopia'), (b'Finland', b'Finland'), (b'Fiji', b'Fiji'), (b'Falkland Islands (Malvinas)', b'Falkland Islands (Malvinas)'), (b'Micronesia, Federated States of', b'Micronesia, Federated States of'), (b'Faroe Islands', b'Faroe Islands'), (b'France', b'France'), (b'France, Metropolitan', b'France, Metropolitan'), (b'Gabon', b'Gabon'), (b'United Kingdom', b'United Kingdom'), (b'Grenada', b'Grenada'), (b'Georgia', b'Georgia'), (b'French Guiana', b'French Guiana'), (b'Ghana', b'Ghana'), (b'Gibraltar', b'Gibraltar'), (b'Greenland', b'Greenland'), (b'Gambia', b'Gambia'), (b'Guinea', b'Guinea'), (b'Guadeloupe', b'Guadeloupe'), (b'Equatorial Guinea', b'Equatorial Guinea'), (b'Greece', b'Greece'), (b'South Georgia and the South Sandwich Islands', b'South Georgia and the South Sandwich Islands'), (b'Guatemala', b'Guatemala'), (b'Guam', b'Guam'), (b'Guinea-Bissau', b'Guinea-Bissau'), (b'Guyana', b'Guyana'), (b'Hong Kong', b'Hong Kong'), (b'Heard Island and McDonald Islands', b'Heard Island and McDonald Islands'), (b'Honduras', b'Honduras'), (b'Croatia', b'Croatia'), (b'Haiti', b'Haiti'), (b'Hungary', b'Hungary'), (b'Indonesia', b'Indonesia'), (b'Ireland', b'Ireland'), (b'Israel', b'Israel'), (b'India', b'India'), (b'British Indian Ocean Territory', b'British Indian Ocean Territory'), (b'Iraq', b'Iraq'), (b'Iran, Islamic Republic of', b'Iran, Islamic Republic of'), (b'Iceland', b'Iceland'), (b'Italy', b'Italy'), (b'Jamaica', b'Jamaica'), (b'Jordan', b'Jordan'), (b'Japan', b'Japan'), (b'Kenya', b'Kenya'), (b'Kyrgyzstan', b'Kyrgyzstan'), (b'Cambodia', b'Cambodia'), (b'Kiribati', b'Kiribati'), (b'Comoros', b'Comoros'), (b'Saint Kitts and Nevis', b'Saint Kitts and Nevis'), (b"Korea, Democratic People's Republic of", b"Korea, Democratic People's Republic of"), (b'Korea, Republic of', b'Korea, Republic of'), (b'Kuwait', b'Kuwait'), (b'Cayman Islands', b'Cayman Islands'), (b'Kazakhstan', b'Kazakhstan'), (b"Lao People's Democratic Republic", b"Lao People's Democratic Republic"), (b'Lebanon', b'Lebanon'), (b'Saint Lucia', b'Saint Lucia'), (b'Liechtenstein', b'Liechtenstein'), (b'Sri Lanka', b'Sri Lanka'), (b'Liberia', b'Liberia'), (b'Lesotho', b'Lesotho'), (b'Lithuania', b'Lithuania'), (b'Luxembourg', b'Luxembourg'), (b'Latvia', b'Latvia'), (b'Libya', b'Libya'), (b'Morocco', b'Morocco'), (b'Monaco', b'Monaco'), (b'Moldova, Republic of', b'Moldova, Republic of'), (b'Madagascar', b'Madagascar'), (b'Marshall Islands', b'Marshall Islands'), (b'Macedonia', b'Macedonia'), (b'Mali', b'Mali'), (b'Myanmar', b'Myanmar'), (b'Mongolia', b'Mongolia'), (b'Macau', b'Macau'), (b'Northern Mariana Islands', b'Northern Mariana Islands'), (b'Martinique', b'Martinique'), (b'Mauritania', b'Mauritania'), (b'Montserrat', b'Montserrat'), (b'Malta', b'Malta'), (b'Mauritius', b'Mauritius'), (b'Maldives', b'Maldives'), (b'Malawi', b'Malawi'), (b'Mexico', b'Mexico'), (b'Malaysia', b'Malaysia'), (b'Mozambique', b'Mozambique'), (b'Namibia', b'Namibia'), (b'New Caledonia', b'New Caledonia'), (b'Niger', b'Niger'), (b'Norfolk Island', b'Norfolk Island'), (b'Nigeria', b'Nigeria'), (b'Nicaragua', b'Nicaragua'), (b'Netherlands', b'Netherlands'), (b'Norway', b'Norway'), (b'Nepal', b'Nepal'), (b'Nauru', b'Nauru'), (b'Niue', b'Niue'), (b'New Zealand', b'New Zealand'), (b'Oman', b'Oman'), (b'Panama', b'Panama'), (b'Peru', b'Peru'), (b'French Polynesia', b'French Polynesia'), (b'Papua New Guinea', b'Papua New Guinea'), (b'Philippines', b'Philippines'), (b'Pakistan', b'Pakistan'), (b'Poland', b'Poland'), (b'Saint Pierre and Miquelon', b'Saint Pierre and Miquelon'), (b'Pitcairn Islands', b'Pitcairn Islands'), (b'Puerto Rico', b'Puerto Rico'), (b'Palestinian Territory', b'Palestinian Territory'), (b'Portugal', b'Portugal'), (b'Palau', b'Palau'), (b'Paraguay', b'Paraguay'), (b'Qatar', b'Qatar'), (b'Reunion', b'Reunion'), (b'Romania', b'Romania'), (b'Russian Federation', b'Russian Federation'), (b'Rwanda', b'Rwanda'), (b'Saudi Arabia', b'Saudi Arabia'), (b'Solomon Islands', b'Solomon Islands'), (b'Seychelles', b'Seychelles'), (b'Sudan', b'Sudan'), (b'Sweden', b'Sweden'), (b'Singapore', b'Singapore'), (b'Saint Helena', b'Saint Helena'), (b'Slovenia', b'Slovenia'), (b'Svalbard and Jan Mayen', b'Svalbard and Jan Mayen'), (b'Slovakia', b'Slovakia'), (b'Sierra Leone', b'Sierra Leone'), (b'San Marino', b'San Marino'), (b'Senegal', b'Senegal'), (b'Somalia', b'Somalia'), (b'Suriname', b'Suriname'), (b'Sao Tome and Principe', b'Sao Tome and Principe'), (b'El Salvador', b'El Salvador'), (b'Syrian Arab Republic', b'Syrian Arab Republic'), (b'Swaziland', b'Swaziland'), (b'Turks and Caicos Islands', b'Turks and Caicos Islands'), (b'Chad', b'Chad'), (b'French Southern Territories', b'French Southern Territories'), (b'Togo', b'Togo'), (b'Thailand', b'Thailand'), (b'Tajikistan', b'Tajikistan'), (b'Tokelau', b'Tokelau'), (b'Turkmenistan', b'Turkmenistan'), (b'Tunisia', b'Tunisia'), (b'Tonga', b'Tonga'), (b'Timor-Leste', b'Timor-Leste'), (b'Turkey', b'Turkey'), (b'Trinidad and Tobago', b'Trinidad and Tobago'), (b'Tuvalu', b'Tuvalu'), (b'Taiwan', b'Taiwan'), (b'Tanzania, United Republic of', b'Tanzania, United Republic of'), (b'Ukraine', b'Ukraine'), (b'Uganda', b'Uganda'), (b'United States Minor Outlying Islands', b'United States Minor Outlying Islands'), (b'United States', b'United States'), (b'Uruguay', b'Uruguay'), (b'Uzbekistan', b'Uzbekistan'), (b'Holy See (Vatican City State)', b'Holy See (Vatican City State)'), (b'Saint Vincent and the Grenadines', b'Saint Vincent and the Grenadines'), (b'Venezuela', b'Venezuela'), (b'Virgin Islands, British', b'Virgin Islands, British'), (b'Virgin Islands, U.S.', b'Virgin Islands, U.S.'), (b'Vietnam', b'Vietnam'), (b'Vanuatu', b'Vanuatu'), (b'Wallis and Futuna', b'Wallis and Futuna'), (b'Samoa', b'Samoa'), (b'Yemen', b'Yemen'), (b'Mayotte', b'Mayotte'), (b'Serbia', b'Serbia'), (b'South Africa', b'South Africa'), (b'Zambia', b'Zambia'), (b'Montenegro', b'Montenegro'), (b'Zimbabwe', b'Zimbabwe'), (b'Anonymous Proxy', b'Anonymous Proxy'), (b'Satellite Provider', b'Satellite Provider'), (b'Other', b'Other'), (b'Aland Islands', b'Aland Islands'), (b'Guernsey', b'Guernsey'), (b'Isle of Man', b'Isle of Man'), (b'Jersey', b'Jersey'), (b'Saint Barthelemy', b'Saint Barthelemy'), (b'Saint Martin', b'Saint Martin'), (b'Bonaire, Sint Eustatius and Saba', b'Bonaire, Sint Eustatius and Saba'), (b'South Sudan', b'South Sudan')])),
            ],
            options={
                'verbose_name': 'attribute: Country',
                'verbose_name_plural': 'attribute: Countries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DocumentType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('can_auto_estimate', models.BooleanField(default=True)),
                ('can_semiauto_estimate', models.BooleanField(default=True)),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Document Type',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Industry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Industry',
                'verbose_name_plural': 'attribute: Industries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Locale',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('lcid', models.IntegerField(unique=True)),
                ('jams_lcid', models.IntegerField(unique=True)),
                ('dvx_lcid', models.IntegerField(unique=True)),
                ('available', models.BooleanField(default=False)),
                ('dvx_log_name', models.CharField(max_length=100, unique=True, null=True, blank=True)),
                ('if_source_no_auto_estimate', models.BooleanField(default=False)),
                ('if_target_no_auto_estimate', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Locale',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PricingBasis',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Pricing Basis',
                'verbose_name_plural': 'attribute: Pricing Bases',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PricingFormula',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('percent_calculation', models.DecimalField(default=0.0, max_digits=10, decimal_places=3)),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Pricing Formula',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PricingScheme',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('obsolete_dvx_subject_code', models.IntegerField(default=0, db_column=b'dvx_subject_code')),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Pricing Scheme',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ScopeUnit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('jams_basisid', models.IntegerField(null=True)),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Scope Unit',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('expansion_rate', models.FloatField(default=1.0)),
                ('formula', models.ForeignKey(blank=True, to='services.PricingFormula', null=True)),
            ],
            options={
                'ordering': ['source', 'target', 'service_type', 'unit_of_measure'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ServiceCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('rank', models.FloatField(verbose_name=b'Display Order')),
                ('verbose_description', models.TextField(default=b'', blank=True)),
            ],
            options={
                'ordering': ['rank'],
                'verbose_name': 'attribute: Service Type Category',
                'verbose_name_plural': 'attribute: Service Type Categories',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('available', models.BooleanField(default=False)),
                ('verbose_description', models.TextField(null=True, blank=True)),
                ('translation_task', models.BooleanField(default=False)),
                ('billable', models.BooleanField(default=True)),
                ('jams_jobtaskid', models.PositiveIntegerField(null=True, blank=True)),
                ('workflow', models.BooleanField(default=True)),
                ('abbreviation', models.CharField(default=b'', max_length=20, blank=True)),
                ('icon', models.CharField(default=b'', max_length=20, blank=True)),
                ('category', models.ForeignKey(blank=True, to='services.ServiceCategory', null=True)),
            ],
            options={
                'ordering': ['category', 'description'],
                'verbose_name': 'attribute: Service Type',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Vertical',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'ordering': ['description'],
                'verbose_name': 'attribute: Vertical',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='service',
            name='service_type',
            field=models.ForeignKey(to='services.ServiceType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='service',
            name='source',
            field=models.ForeignKey(related_name=b'services_as_source', blank=True, to='services.Locale', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='service',
            name='target',
            field=models.ForeignKey(related_name=b'services_as_target', blank=True, to='services.Locale', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='service',
            name='unit_of_measure',
            field=models.ForeignKey(to='services.ScopeUnit', max_length=10),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='service',
            unique_together=set([('service_type', 'unit_of_measure', 'source', 'target')]),
        ),
    ]
