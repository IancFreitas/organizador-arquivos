# Organizador de Arquivos

![CI](https://github.com/IancFreitas/organizador-arquivos/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![Licença](https://img.shields.io/badge/licen%C3%A7a-MIT-green)

Automação em Python que organiza pastas bagunçadas (como a de **Downloads**) movendo cada arquivo
para uma subpasta de acordo com o tipo: `Imagens`, `Documentos`, `Planilhas`, `Videos` etc.

Usa só a biblioteca padrão do Python, sem nenhuma dependência externa.

## Funcionalidades

- **Organização por tipo** com categorias padrão ou personalizadas via arquivo TOML
- **Modo simulação** (`--simular`): mostra o que seria feito sem mover nada
- **Subpastas por data** (`--por-data`): `Documentos/2026-03/relatorio.pdf`
- **Modo monitoramento** (`--monitorar`): fica rodando e organiza cada arquivo novo que aparecer
- **Desfazer**: toda execução fica registrada em um histórico, e `desfazer` restaura a última
- **Seguro por padrão**:
  - nunca sobrescreve arquivos (`foto.png` vira `foto (1).png`);
  - ignora arquivos ocultos e downloads em andamento (`.crdownload`, `.part`, `.tmp`);
  - no modo monitoramento, espera o arquivo parar de ser gravado antes de movê-lo.

## Instalação

```bash
git clone https://github.com/IancFreitas/organizador-arquivos.git
cd organizador-arquivos
pip install .
```

## Uso

```bash
# Ver o que seria feito, sem mover nada
organizador organizar ~/Downloads --simular

# Organizar de verdade
organizador organizar ~/Downloads

# Organizar separando também por mês
organizador organizar ~/Downloads --por-data

# Ficar monitorando a pasta (verifica a cada 30 segundos)
organizador organizar ~/Downloads --monitorar --intervalo 30

# Voltou atrás? Desfaz a última organização
organizador desfazer ~/Downloads
```

Exemplo de saída:

```
$ organizador organizar ~/Downloads --simular
[simulação] foto.png -> Imagens/foto.png
[simulação] musica.mp3 -> Audios/musica.mp3
[simulação] relatorio.pdf -> Documentos/relatorio.pdf
[simulação] setup.exe -> Instaladores/setup.exe
[simulação] vendas.csv -> Planilhas/vendas.csv

5 arquivo(s) seriam movidos:
  Imagens         1
  Audios          1
  Documentos      1
  Instaladores    1
  Planilhas       1
```

### Categorias personalizadas

Crie um arquivo TOML (veja [`config.exemplo.toml`](config.exemplo.toml)):

```toml
[categorias]
Fotos = ["jpg", "jpeg", "png"]
Faculdade = ["pdf", "docx", "pptx"]
```

```bash
organizador organizar ~/Downloads --config minhas-categorias.toml
```

Extensões que não estiverem em nenhuma categoria vão para `Outros`.

### Rodar automaticamente

**Windows (Agendador de Tarefas)**: crie uma tarefa que rode ao fazer login:

```powershell
schtasks /create /tn "Organizar Downloads" /sc onlogon /tr "organizador organizar %USERPROFILE%\Downloads --monitorar"
```

**Linux/macOS (cron)**: organizar todo dia às 18h:

```cron
0 18 * * * organizador organizar ~/Downloads
```

## Como funciona

```
src/organizador
├── config.py      Categorias padrão e leitura/validação do TOML
├── organizer.py   Planeja os movimentos, executa, registra histórico e desfaz
└── cli.py         Interface de linha de comando (argparse)
```

A lógica é separada em duas etapas: `plan_moves` só **calcula** o destino de cada arquivo, sem tocar
no disco, e `apply_moves` **executa** o plano. É isso que torna o modo simulação trivial
e a lógica fácil de testar.

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest       # testes
ruff check . # lint
```

Os testes rodam no GitHub Actions em Windows e Linux, com Python 3.11, 3.12 e 3.13.
