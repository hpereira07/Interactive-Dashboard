import re
from pathlib import Path
import pandas as pd
import plotly.express as px
from shiny import reactive, render, req
from shiny.express import input, ui
from shinywidgets import render_plotly

# Configuração
DATA_DIR = Path("data")
CATEGORIES_CSV = Path("categories.csv")  # opcional; se existir, aplica mapeamentos
TOL = 0.01  # tolerância para comparação de totais (em €)

ui.page_opts(title="Débitos Diretos (PS2)", fillable=True)

# Tipo 1: 1 + AAAAMMDD + ENTIDADE (texto) + resto numérico
header_pattern = re.compile(r"^1(?P<data>\d{8})(?P<entidade>[^0-9]+)(?P<resto>\d.*)$")
# Tipo 2: 2 + bloco numérico + descrição (texto livre)
detail_pattern = re.compile(r"^2(?P<num>\d+)(?P<desc>.*)$")
# Tipo 9: 9 + dígitos (14 para total + 6 para nº operações)
footer_pattern = re.compile(r"^9(?P<totais>\d+)$")

def read_text_with_fallback(path: Path) -> str:
    """Tenta ler o ficheiro com várias codificações."""
    encodings = ["utf-8", "latin-1", "cp1252"]
    last_err = None
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except Exception as e:
            last_err = e
    raise last_err

# Parsing PS2
def parse_ps2_file(path: Path) -> pd.DataFrame:
    """
    Lê um ficheiro PS2 e devolve um DataFrame com linhas de detalhe (Tipo 2).
    Layout (exemplo):
    - Tipo 1: '1' + AAAAMMDD + ENTIDADE (texto) + campos numéricos
    - Tipo 2: '2' + bloco numérico + VALOR em cêntimos (últimos 14 dígitos) + DESCRIÇÃO
    - Tipo 9: '9' + TOTAL (14 dígitos, cêntimos) + Nº OPERAÇÕES (6 dígitos)
    """
    text = read_text_with_fallback(path)
    lines = text.splitlines()

    entidade = None
    data_proc = None
    detalhes = []
    valor_total_rodape = None
    n_ops_rodape = None
    seq_det = 0  # contador de clientes (linhas tipo 2) no ficheiro

    for line in lines:
        if not line:
            continue
        tipo = line[0]

        if tipo == "1":
            m = header_pattern.match(line)
            if m:
                data_proc = m.group("data")
                entidade = m.group("entidade").strip()
            else:
                # Fallback: tenta extrair data e entidade
                data_proc = line[1:9] if len(line) >= 9 else None
                rest = line[9:] if len(line) > 9 else ""
                ent_match = re.match(r"([^0-9]+)", rest)
                entidade = ent_match.group(1).strip() if ent_match else "DESCONHECIDA"

        elif tipo == "2":
            m = detail_pattern.match(line)
            if not m:
                continue
            nums = m.group("num")
            desc = m.group("desc").strip()

            # Valor: últimos 14 dígitos do bloco numérico (cêntimos)
            if len(nums) >= 14 and nums[-14:].isdigit():
                valor_cent = int(nums[-14:])
                outros = nums[:-14]
            else:
                valor_cent = 0
                outros = nums

            # Atribuição de cliente por ordem de aparecimento
            seq_det += 1
            cliente_id = seq_det
            cliente_lbl = f"Cliente {cliente_id:03d}"

            detalhes.append({
                "ficheiro": path.name,
                "data_processamento": pd.to_datetime(data_proc, format="%Y%m%d", errors="coerce"),
                "entidade": entidade,
                "descricao": desc,
                "valor_eur": valor_cent / 100.0,
                "campos_numericos": outros,
                "cliente_id": cliente_id,
                "cliente": cliente_lbl,
            })

        elif tipo == "9":
            m = footer_pattern.match(line)
            if m:
                totals = m.group("totais")
                # 14 dígitos para montante + 6 para nº operações
                if len(totals) >= 20 and totals[:14].isdigit() and totals[14:20].isdigit():
                    valor_total_rodape = int(totals[:14]) / 100.0
                    n_ops_rodape = int(totals[14:20])
                else:
                    # Fallback raro
                    try:
                        valor_total_rodape = int(totals[-14:]) / 100.0
                    except Exception:
                        valor_total_rodape = None
                    try:
                        prefix = totals[:-14]
                        n_ops_rodape = int(prefix) if prefix.isdigit() else None
                    except Exception:
                        n_ops_rodape = None

    df = pd.DataFrame(detalhes)
    if not df.empty:
        df["data"] = df["data_processamento"]
        df["ano_mes"] = df["data"].dt.to_period("M").astype(str)
        # Propaga info do rodapé por linha (para validar por ficheiro)
        df["total_rodape_eur"] = valor_total_rodape
        df["n_ops_rodape"] = n_ops_rodape

        # Atributos úteis (opcional)
        if valor_total_rodape is not None:
            df.attrs["total_rodape_eur"] = valor_total_rodape
            df.attrs["n_ops_rodape"] = n_ops_rodape
            df.attrs["total_calc_eur"] = round(df["valor_eur"].sum(), 2)

    return df

# Categorias (mapeamento por regex)
DEFAULT_RULES = pd.DataFrame(
    {
        "padrao": [r"fatura\s+eletricidade|energia|luz"],
        "categoria": ["Eletricidade"],
        "campo": ["descricao"],
    }
)

@reactive.calc
def regras_categorias() -> pd.DataFrame:
    if CATEGORIES_CSV.exists():
        try:
            df = pd.read_csv(CATEGORIES_CSV)
            req({"padrao", "categoria"}.issubset(set(df.columns)))
            if "campo" not in df.columns:
                df["campo"] = "descricao"
            return df
        except Exception:
            return DEFAULT_RULES
    return DEFAULT_RULES


def aplicar_categorias(df: pd.DataFrame, regras: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["categoria"] = "Não classificado"
    for _, r in regras.iterrows():
        padrao = re.compile(str(r["padrao"]), re.IGNORECASE)
        campo = r.get("campo", "descricao")
        mask = df[campo].astype(str).str.contains(padrao)
        df.loc[mask, "categoria"] = r["categoria"]
    return df

# Carregamento dos dados (/data)
@reactive.calc
def dados_brutos() -> pd.DataFrame:
    files = sorted(
        list(DATA_DIR.glob("*.ps2"))
        + list(DATA_DIR.glob("*.txt"))
        + list(DATA_DIR.glob("*.dat"))
    )
    dfs = [parse_ps2_file(f) for f in files]
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame(
        columns=[
            "ficheiro", "data_processamento", "entidade", "descricao",
            "valor_eur", "campos_numericos", "data", "ano_mes",
            "total_rodape_eur", "n_ops_rodape",
            "cliente_id", "cliente",
        ]
    )

# Dados + Validação por ficheiro
@reactive.calc
def dados() -> pd.DataFrame:
    base = aplicar_categorias(dados_brutos(), regras_categorias())
    if base.empty:
        return base

    # Relatório de validação por ficheiro
    agrup = base.groupby("ficheiro", as_index=False).agg(
        total_calc_eur=("valor_eur", "sum"),
        n_det=("ficheiro", "size"),
        total_rodape_eur=("total_rodape_eur", "max"),
        n_ops_rodape=("n_ops_rodape", "max"),
        entidade=("entidade", "first"),
        data_proc=("data_processamento", "first"),
    )

    def _msg_validacao(row) -> str:
        tem_cabecalho = pd.notna(row["data_proc"])
        tem_rodape = pd.notna(row["total_rodape_eur"]) and pd.notna(row["n_ops_rodape"])

        msgs = []
        ok = True

        if not tem_cabecalho:
            msgs.append("Erro: Cabeçalho ausente ou inválido.")
            ok = False
        if not tem_rodape:
            msgs.append("Erro: Rodapé ausente ou inválido.")
            ok = False

        if tem_rodape:
            total_calc = round(float(row["total_calc_eur"]), 2)
            total_rodape = round(float(row["total_rodape_eur"]), 2)
            if abs(total_calc - total_rodape) > TOL:
                msgs.append(
                    f"Erro: Total calculado (€{total_calc:,.2f}) difere do rodapé (€{total_rodape:,.2f})."
                )
                ok = False

            try:
                n_det = int(row["n_det"])
                n_ops = int(row["n_ops_rodape"])
                if n_det != n_ops:
                    msgs.append(
                        f"Erro: Nº de operações ({n_ops}) difere das linhas detalhe ({n_det})."
                    )
                    ok = False
            except Exception:
                msgs.append("Erro: Nº de operações no rodapé não é numérico.")
                ok = False

        if ok:
            return "Válido"
        else:
            return " ; ".join(msgs)

    agrup["validacao_msg"] = agrup.apply(_msg_validacao, axis=1)

    # Junta a mensagem ao DataFrame base
    out = base.merge(agrup[["ficheiro", "validacao_msg"]], on="ficheiro", how="left")
    return out

# Sidebar (filtros)
with ui.sidebar(open="desktop"):
    ui.input_text("periodo_ini", "Início (AAAA-MM)", "")
    ui.input_text("periodo_fim", "Fim (AAAA-MM)", "")
    ui.input_select("entidade", "Entidade", choices=[], multiple=True)
    ui.input_slider("montante", "Montante (€)", min=0, max=1000, value=[0, 1000], step=1)
    ui.input_text("pesquisa", "Pesquisa (texto)", "")

# Inicialização dinâmica de escolhas e limites
@reactive.effect
def _init_sidebar():
    df = dados()
    entidades = sorted(df["entidade"].dropna().unique().tolist()) if not df.empty else []
    ui.update_select("entidade", choices=entidades)
    if not df.empty:
        vmax = float(df["valor_eur"].max())
        ui.update_slider("montante", min=0, max=max(100.0, round(vmax + 5)), value=[0, round(vmax + 5)])
        meses = sorted(df["ano_mes"].dropna().unique().tolist())
        if meses:
            ui.update_text("periodo_ini", value=meses[0])
            ui.update_text("periodo_fim", value=meses[-1])

# Filtragem reativa
@reactive.calc
def dados_filtrados() -> pd.DataFrame:
    df = dados()
    if df.empty:
        return df
    out = df.copy()

    # Filtro por entidade
    ent = input.entidade()
    if ent:
        out = out[out["entidade"].isin(ent)]

    # Filtro por montante
    rng = input.montante()
    out = out[out["valor_eur"].between(float(rng[0]), float(rng[1]))]

    # Filtro por período AAAA-MM
    ini = input.periodo_ini().strip()
    fim = input.periodo_fim().strip()
    if ini:
        out = out[out["ano_mes"] >= ini]
    if fim:
        out = out[out["ano_mes"] <= fim]

    # Pesquisa texto livre
    txt = input.pesquisa().strip().lower()
    if txt:
        mask = (
            out["descricao"].astype(str).str.lower().str.contains(txt)
            | out["entidade"].astype(str).str.lower().str.contains(txt)
        )
        out = out[mask]

    return out

# ---------------------------------------
# KPI Boxes
# ---------------------------------------
with ui.layout_columns(fill=False):
    with ui.value_box():
        "Operações"

        @render.express
        def kpi_ops():
            df = dados_filtrados()
            df.shape[0]

    with ui.value_box():
        "Total"

        @render.express
        def kpi_total():
            df = dados_filtrados()
            total = df["valor_eur"].sum() if not df.empty else 0.0
            f"€{total:,.2f}"

    with ui.value_box():
        "Custo Médio"

        @render.express
        def kpi_ticket():
            df = dados_filtrados()
            n = df.shape[0]
            avg = (df["valor_eur"].sum() / n) if n else 0.0
            f"€{avg:,.2f}"

# ---------------------------------------
# Tabela de detalhe (com coluna "Validação")
# ---------------------------------------
with ui.card(full_screen=True):
    ui.card_header("Detalhe de Débitos")

    @render.data_frame
    def tabela():
        df = dados_filtrados()
        df["Data"] = df["data"].dt.strftime("%Y-%m-%d")  # <-- NOVO
        df["Entidade"] = df["entidade"]
        df["Descrição"] = df["descricao"]
        df["Categoria"] = df["categoria"]
        df["Custo (€)"] = df["valor_eur"]
        df["Ficheiro"] = df["ficheiro"]
        df["Validação"] = df.get("validacao_msg", "—")

        mostrar = df[
            ["Data", "Entidade", "Descrição", "Categoria", "Custo (€)", "Ficheiro", "Validação"]
        ].copy() if not df.empty else df

        return render.DataGrid(mostrar)

# ---------------------------------------
# Gráficos (linha e barras)
# ---------------------------------------
with ui.layout_columns(col_widths=[6, 6]):
    # Evolução mensal (total)
    with ui.card(full_screen=True):
        ui.card_header("Evolução Mensal (Total)")

        @render_plotly
        def graf_mes():
            df = dados_filtrados()
            if df.empty:
                return px.line()
            g = df.groupby("ano_mes", as_index=False)["valor_eur"].sum()
            fig = px.line(g, x="ano_mes", y="valor_eur", markers=True)
            fig.update_layout(xaxis_title="Mês", yaxis_title="Total (€)")
            return fig

    # Evolução mensal por cliente
    with ui.card(full_screen=True):
        ui.card_header("Evolução Mensal (Cliente)")

        @render_plotly
        def graf_clientes():
            df = dados_filtrados()
            if df.empty or "cliente" not in df.columns:
                return px.line()

            # Séries mensais por cliente
            g = df.groupby(["ano_mes", "cliente"], as_index=False)["valor_eur"].sum()

            # Limitar a Top-N clientes para legibilidade (N=20)
            topN = 20
            top_clientes = (
                g.groupby("cliente", as_index=False)["valor_eur"]
                 .sum()
                 .sort_values("valor_eur", ascending=False)
                 .head(topN)["cliente"]
            )
            g2 = g[g["cliente"].isin(top_clientes)]

            fig = px.line(
                g2, x="ano_mes", y="valor_eur", color="cliente",
                markers=True,
            )
            fig.update_layout(
                xaxis_title="Mês",
                yaxis_title="Total (€)",
                legend_title_text="Cliente",
                hovermode="x unified"
            )
            return fig

# Por Entidade
with ui.card(full_screen=True):
    ui.card_header("Por Entidade")

    @render_plotly
    def graf_ent():
        df = dados_filtrados()
        if df.empty:
            return px.bar()
        g = (
            df.groupby("entidade", as_index=False)["valor_eur"]
            .sum()
            .sort_values("valor_eur", ascending=False)
        )
        fig = px.bar(g, x="entidade", y="valor_eur")
        fig.update_layout(xaxis_title="Entidade", yaxis_title="Total (€)")
        return fig

# Recarregar (invalida cálculos reativos)
@reactive.effect
@reactive.event(input.recarregar)
def _reload():
    _ = dados()