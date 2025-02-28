# Configuração para Raspberry Pi

Este guia contém instruções para configurar o Monitor de Produtos em Espera em um Raspberry Pi.

## Requisitos

- Raspberry Pi (testado em Raspberry Pi 3 ou superior)
- Raspbian OS (Buster ou mais recente)
- Conexão com internet

## Instalação de Dependências

Execute os seguintes comandos para instalar as dependências necessárias:

```bash
# Atualizar repositórios
sudo apt update
sudo apt upgrade -y

# Instalar Python e pip
sudo apt install -y python3 python3-pip

# Instalar dependências para conexão com SQL Server
sudo apt install -y freetds-bin freetds-dev unixodbc unixodbc-dev tdsodbc

# Instalar dependências Python
pip3 install -r requirements.txt
```

## Configuração do FreeTDS

1. Edite o arquivo de configuração do FreeTDS:

```bash
sudo nano /etc/freetds/freetds.conf
```

2. Adicione a seguinte configuração (substitua os valores conforme necessário):

```
[MSSQL]
    host = seu_servidor_sql
    port = 1433
    tds version = 7.4
    client charset = UTF-8
```

3. Teste a conexão com o servidor:

```bash
tsql -S MSSQL -U seu_usuario -P sua_senha
```

## Configuração do ODBC

1. Edite o arquivo odbcinst.ini:

```bash
sudo nano /etc/odbcinst.ini
```

2. Adicione:

```
[FreeTDS]
Description = FreeTDS Driver
Driver = /usr/lib/arm-linux-gnueabihf/odbc/libtdsodbc.so
Setup = /usr/lib/arm-linux-gnueabihf/odbc/libtdsS.so
FileUsage = 1
```

3. Edite o arquivo odbc.ini:

```bash
sudo nano /etc/odbc.ini
```

4. Adicione:

```
[MSSQL]
Driver = FreeTDS
Server = seu_servidor_sql
Port = 1433
Database = seu_banco_de_dados
TDS_Version = 7.4
ClientCharset = UTF-8
```

## Executando a Aplicação

```bash
python3 app.py
```

## Solução de Problemas

### Erro de Driver

Se encontrar erros relacionados ao driver, verifique se o caminho do driver está correto em `/etc/odbcinst.ini`. Em algumas versões do Raspberry Pi, o caminho pode ser diferente.

### Teste de Conexão

Use o comando a seguir para testar a conexão ODBC:

```bash
isql -v MSSQL seu_usuario sua_senha
```

### Logs

Verifique os logs da aplicação em `db_connection.log` para diagnóstico de problemas de conexão.