# Monitor de Produtos em Espera

Um aplicativo web Flask para monitorar produtos em espera no sistema de pedidos, permitindo o acompanhamento de pedidos pendentes e completados.

## Descrição

Este sistema permite o monitoramento em tempo real de produtos em espera, oferecendo uma interface web para visualizar pedidos pendentes, marcar pedidos como completados e visualizar estatísticas. O aplicativo se conecta a um banco de dados SQL Server para obter informações sobre pedidos e pode funcionar em modo offline usando dados simulados quando necessário.

## Funcionalidades

- Visualização de pedidos pendentes em tempo real
- Marcação de pedidos como completados
- Histórico de pedidos completados
- Estatísticas de produtos por separador
- Modo offline para testes sem conexão com banco de dados
- Interface responsiva para uso em diferentes dispositivos

## Requisitos

- Python 3.8 ou superior
- SQL Server com driver ODBC
- Dependências Python listadas em `requirements.txt`

## Instalação

1. Clone o repositório:

```bash
git clone <url-do-repositorio>
cd monitor-produtosespera
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
```

3. Instale as dependências:

```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente (veja a seção de Configuração)

## Configuração

Crie um arquivo `.env` na raiz do projeto com as seguintes variáveis:

```
DB_SERVER=seu_servidor_sql
DB_DATABASE=nome_do_banco
DB_USERNAME=usuario
DB_PASSWORD=senha
DB_PORT=1433
DB_TIMEOUT=30
DB_RETRIES=3
DB_RETRY_DELAY=5
DB_SCHEMA=dbo
OFFLINE_MODE=false
```

### Opções de Configuração

- `DB_SERVER`: Endereço do servidor SQL Server
- `DB_DATABASE`: Nome do banco de dados
- `DB_USERNAME`: Nome de usuário para autenticação
- `DB_PASSWORD`: Senha para autenticação
- `DB_PORT`: Porta do servidor SQL Server (padrão: 1433)
- `DB_TIMEOUT`: Tempo limite para conexão em segundos (padrão: 30)
- `DB_RETRIES`: Número de tentativas de reconexão (padrão: 3)
- `DB_RETRY_DELAY`: Tempo de espera entre tentativas em segundos (padrão: 5)
- `DB_SCHEMA`: Schema do banco de dados (padrão: dbo)
- `OFFLINE_MODE`: Ativar modo offline para testes sem banco de dados (true/false)
- `COMPLETION_TRACKING_TIME`: Horas para rastrear pedidos completados (padrão: 48)

## Execução

Para iniciar o aplicativo:

```bash
python app.py
```

O aplicativo estará disponível em `http://localhost:5000`

## Estrutura do Projeto

- `app.py`: Arquivo principal da aplicação Flask
- `utils/`: Módulos utilitários
  - `db_connection.py`: Gerenciamento de conexão com banco de dados
  - `db_explorer.py`: Exploração de esquemas e tabelas do banco
  - `mock_data.py`: Dados simulados para modo offline
- `templates/`: Templates HTML
- `static/`: Arquivos estáticos (CSS, JavaScript, imagens)
- `data/`: Armazenamento de dados de pedidos completados

## Modo Offline

Para executar o aplicativo sem conexão com o banco de dados, defina `OFFLINE_MODE=true` no arquivo `.env`. Isso usará dados simulados para testes.

## Licença

Este projeto é proprietário e confidencial.