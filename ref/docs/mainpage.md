
# Débitos Diretos (PS2)

> **Objetivo**: Ler ficheiros **PS2** de débitos diretos, **validar totais**, aplicar **categorização por regex** e expor um **dashboard** interativo com *Shiny para Python* + *Plotly*.

## Visão Geral
- **Entrada**: ficheiros `*.ps2`/`*.txt`/`*.dat` em `./data/`.
- **Parsing**: `parse_ps2_file()` extrai cabeçalho (Tipo 1), detalhes (Tipo 2) e rodapé (Tipo 9).
- **Validação**: compara o total calculado com o total de rodapé e o nº de operações.
- **Categorização**: aplica regras (regex) via `categories.csv` (ou `DEFAULT_RULES`).
- **UI**: filtros (sidebar), KPIs, tabela de detalhe, gráficos de evolução e por entidade.

### Pipeline de Dados
```
Ficheiros PS2 → read_text_with_fallback → parse_ps2_file → dados_brutos
            → aplicar_categorias + regras_categorias → dados (validação)
            → filtros de UI → dados_filtrados → KPIs/Tabela/Gráficos
```

### Estrutura do Repositório
```
├─ src/            # código do projeto (app.py e restantes .py)
├─ data/           # ficheiros PS2
├─ doc/            # relatório em LaTeX (ficheiros .tex, .bib, .pdf)
├─ ref/            # documentação de código (Doxygen) -> saída HTML
│  ├─ Doxyfile     # Doxyfile
│  └─ docs/        # páginas Markdown usadas pelo Doxygen
└─ README.md       # informação geral

```

## Componentes
- **Parser/Leitura** (*grupo*: `parser_ps2`):
  - `read_text_with_fallback(path)`
  - `parse_ps2_file(path)`
  - `dados_brutos()`
- **Categorização** (*grupo*: `categorizacao`):
  - `regras_categorias()`
  - `aplicar_categorias(df, regras)`
- **Validação** (*grupo*: `validacao`):
  - `dados()` (mensagem `validacao_msg` por ficheiro)
- **UI & Métricas** (*grupo*: `ui`):
  - `_init_sidebar()`
  - `dados_filtrados()`
  - `kpi_ops`, `kpi_total`, `kpi_ticket`
  - `tabela`, `graf_mes`, `graf_clientes`, `graf_ent`

## Como Gerar a Documentação
```bash
sudo apt-get install doxygen
pip install doxypypy
# na raiz do projeto
doxygen Doxyfile
# abrir docs/build/html/index.html
```

## Ligações
- \ref architecture_page "Arquitetura"
- \ref ps2_format_page "Formato PS2"
- \ref howto_page "Como usar"
- \ref dev_guide_page "Guia de desenvolvimento"
