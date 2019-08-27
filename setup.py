# coding: utf-8

from setuptools import setup, find_packages

NAME = "apirecintos"
VERSION = "0.9"

# To install the library, run the following
#
# python setup.py install
#
# prerequisite: setuptools
# http://pypi.python.org/pypi/setuptools

REQUIRES = ["connexion[swagger-ui]",
            "dateutils",
            "gunicorn",
            "mysql-connector",
            "requests",
            "sqlalchemy"
            ]

setup(
    name=NAME,
    version=VERSION,
    description="APIRecintos",
    author_email="ivan.brasilico@rfb.gov.br",
    url="",
    keywords=["Swagger", "APIRecintos"],
    install_requires=REQUIRES,
    extras_require={
        'dev': [
            'mkdocs',
            'pytest',
            'pytest-pep8',
            'pytest-cov',
            'tox'
        ]
    },
    packages=find_packages(),
    package_data={'OpenAPI3.0.1': ['apiserver/openapi.yaml']},
    include_package_data=True,
    entry_points={
        'console_scripts': ['apiserver=apiserver.main:main',
                            'apiclient=cli.cliente_api:carrega']},
    long_description="""\
    API para prestação de informações sobre eventos de controle aduaneiro a cargo dos Redex,
     Recintos, Operadores Portuários e demais intervenientes em carga sobre controle aduaneiro.
    """
)
