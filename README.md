[![Build Status](https://travis-ci.org/IvanBrasilico/ade02rest.svg?branch=master)](https://travis-ci.org/IvanBrasilico/ade02rest) 
[![codecov](https://codecov.io/gh/IvanBrasilico/ade02rest/branch/master/graph/badge.svg)](https://codecov.io/gh/IvanBrasilico/ade02rest)


# ade02rest

Especificação, testes e protótipo de API Rest para controle de eventos de controle de carga em recintos e áreas sujeitos a controle aduaneiro.

Ver Arquivo openapi.yaml


## Instalação
#### Baixar o conteúdo e criar ambiente virtual para instalação 
```
$git clone https://github.com/IvanBrasilico/ade02rest
$cd ade02rest
$python3 -m venv venv
$. venv/bin/activate
```

#### Instalar dependências e configurar 
```
(venv)$python setup.py install 
```
OU
```
(venv)$pip install -e .
```

#### Instalar dependências e configurar para desenvolvimento 
```
(venv)$python setup.py develop
```
OU
```
(venv)$pip install -e .[dev]
```


#### Rodar sistema
```
$apirecintos
```
MODO DEBUG
```
$python apiserver/main.py
```


### Rodar validador de arquivo/uploader
```
$apicliente
```
OU
```
(venv)$python cli/cliente_api.py
```
O COMANDO ABAIXO GERA UM ARQUIVO EXECUTÁVEL DO VALIDADOR
```
(venv)$pip install pyinstaller
(venv)$pyinstaller --one-file cli/cliente_api.py
```

#### Rodar testes
Testes unitários e de integração:
```
$pytest tests/
```
Rodar todos os testes e checagens via tox (ver tox.ini):
```
$tox
```
