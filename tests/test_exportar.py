"""Testes de `dados_sinteticos.exportar`.

Escritos ANTES do exportador: são a especificação da etapa 1.7. Enquanto
`exportar.py` estiver vazio, todos falham com ImportError.

POR QUE OS IMPORTS SÃO LOCAIS: import no topo faria o pytest abortar a COLETA
inteira e nenhum outro teste do projeto rodaria. Com import dentro de cada
teste, a suíte continua verde no resto e só estes ficam vermelhos — que é o
comportamento útil enquanto o módulo não existe.

NENHUM TESTE ESCREVE EM `raw/` DE VERDADE: todos usam `tmp_path`. É para isso
que `exportar()` recebe a raiz como argumento em vez de assumir o diretório do
projeto.
"""

import json

import pytest

from dados_sinteticos.parametros import CONTAS_PADRAO, SEMENTE_PADRAO

# ---------------------------------------------------------------------------
# Amostras de registro já renderizados, no formato de cada fonte.
# Pequenas e escritas à mão de propósito: testar sujeira contra 21 mil leads
# gerados esconderia o que exatamente mudou.
# ---------------------------------------------------------------------------
INSIGHTS = [
    {
        "date_start": "2026-03-02",
        "date_stop": "2026-03-02",
        "campaign_id": "23800001",
        "campaign_name": "PROSPECÇÃO | Lookalike 1%",
        "spend": 1234.56,
        "impressions": 45231,
        "clicks": 892,
        "account_id": "act_1029384756",
    },
    {
        "date_start": "2026-03-03",
        "date_stop": "2026-03-03",
        "campaign_id": "23800001",
        "campaign_name": "PROSPECÇÃO | Lookalike 1%",
        "spend": 980.10,
        "impressions": 31002,
        "clicks": 640,
        "account_id": "act_1029384756",
    },
    {
        "date_start": "2026-03-02",
        "date_stop": "2026-03-02",
        "campaign_id": "23800002",
        "campaign_name": "REMARKETING | 30 dias",
        "spend": 410.00,
        "impressions": 12004,
        "clicks": 310,
        "account_id": "act_1029384756",
    },
]

CONTATOS = [
    {
        "contact_id": f"0010000{i:02d}",
        "email": f"pessoa{i}@exemplo.com.br",
        "nome": f"Pessoa {i}",
        "telefone": "(11) 90000-0000",
        "data_criacao": "2026-03-02T09:12:00-03:00",
        "score_fit": 72,
        "utm_source": "facebook_ads",
        "utm_medium": "cpc",
        "utm_campaign": "lookalike_1",
    }
    for i in range(100)
]

NEGOCIOS = [
    {
        "deal_id": f"9010000{i:02d}",
        "contact_id": f"0010000{i:02d}",
        "utm_campaign": "23800001" if i % 2 else "23800002",
        "campaign_source": "23800001" if i % 2 else "23800002",
        "valor": 3500.0,
        "status": "ganho",
    }
    for i in range(40)
]


# ===========================================================================
# Escritores — o único lugar do módulo que toca em disco
# ===========================================================================
def test_csv_do_financeiro_usa_ponto_e_virgula_e_virgula_decimal(tmp_path):
    """Convenção exclusiva do financeiro (contrato, 5.5). O separador de
    milhar é ponto e o decimal é vírgula: `3.450,00`."""
    from dados_sinteticos.exportar import _escrever_csv

    caminho = tmp_path / "financeiro_margens.csv"
    _escrever_csv(
        [{"deal_id": "901", "receita_bruta": 3450.0, "margem_percentual": 0.32}],
        caminho,
        sep=";",
        decimal=",",
    )
    texto = caminho.read_text(encoding="utf-8")
    assert "deal_id;receita_bruta;margem_percentual" in texto
    assert "3.450,00" in texto
    assert "0,32" in texto


def test_csv_do_crm_usa_virgula_e_ponto_decimal(tmp_path):
    """O CRM usa a outra convenção. Mesmo escritor, outra configuração — e sem
    separador de milhar, porque o contrato (5.2) exige `^\\d+(\\.\\d{1,2})?$`."""
    from dados_sinteticos.exportar import _escrever_csv

    caminho = tmp_path / "crm_negocios.csv"
    _escrever_csv([{"deal_id": "901", "valor": 3450.0}], caminho, sep=",", decimal=".")
    texto = caminho.read_text(encoding="utf-8")
    assert "3450.00" in texto
    assert "3.450" not in texto


def test_csv_nao_cria_linha_em_branco_no_windows(tmp_path):
    """`csv.writer` sem `newline=""` escreve \\r\\r\\n no Windows, e todo leitor
    vê uma linha vazia entre cada registro. Erro clássico, invisível no editor."""
    from dados_sinteticos.exportar import _escrever_csv

    caminho = tmp_path / "x.csv"
    _escrever_csv([{"a": 1}, {"a": 2}], caminho)
    assert b"\r\r\n" not in caminho.read_bytes()


def test_csv_e_utf8(tmp_path):
    """O contrato (seção 4) exige UTF-8. No Windows o default é a codepage
    ANSI, então isto precisa ser explícito — e falha com acento."""
    from dados_sinteticos.exportar import _escrever_csv

    caminho = tmp_path / "x.csv"
    _escrever_csv([{"segmento": "Saúde / odontologia"}], caminho)
    assert "Saúde / odontologia" in caminho.read_text(encoding="utf-8")


def test_json_e_paginado_com_cursor(tmp_path):
    """A Graph API pagina. Se a ingestão ler só a primeira página, perde a maior
    parte do custo — e o CAC despenca sem ninguém perceber."""
    from dados_sinteticos.exportar import _escrever_json_paginado

    registros = [dict(INSIGHTS[0], date_start=f"2026-03-{d:02d}") for d in range(1, 21)]
    paginas = _escrever_json_paginado(registros, tmp_path, "meta_ads_insights", 7)

    assert len(paginas) == 3  # 20 registros, 7 por página
    primeira = json.loads(paginas[0].read_text(encoding="utf-8"))
    assert len(primeira["data"]) == 7
    assert primeira["paging"]["cursors"]["after"]
    assert primeira["paging"]["next"]


def test_ultima_pagina_nao_tem_next(tmp_path):
    """É `next` ausente que diz à ingestão onde parar."""
    from dados_sinteticos.exportar import _escrever_json_paginado

    registros = [dict(INSIGHTS[0]) for _ in range(10)]
    paginas = _escrever_json_paginado(registros, tmp_path, "meta_ads_insights", 4)
    ultima = json.loads(paginas[-1].read_text(encoding="utf-8"))
    assert ultima["paging"].get("next") is None


def test_concatenar_paginas_recupera_tudo(tmp_path):
    """Paginar não pode perder nem duplicar registro."""
    from dados_sinteticos.exportar import _escrever_json_paginado

    registros = [dict(INSIGHTS[0], clicks=i) for i in range(23)]
    paginas = _escrever_json_paginado(registros, tmp_path, "meta_ads_insights", 5)
    juntos = [linha for p in paginas for linha in json.loads(p.read_text(encoding="utf-8"))["data"]]
    assert len(juntos) == 23
    # int e nao str: converter numero em texto e trabalho de
    # `sujar_numeros_como_texto`, nao do escritor. Misturar as duas coisas
    # tornaria a sujeira impossivel de testar isolada.
    assert [linha["clicks"] for linha in juntos] == list(range(23))


# ===========================================================================
# Sujeiras — funções puras, testadas uma a uma
# ===========================================================================
def test_numeros_viram_texto():
    """A Graph API entrega TODO número como string, inclusive `impressions`.
    Não é nossa invenção: é o comportamento real."""
    from dados_sinteticos.exportar import sujar_numeros_como_texto

    sujos = sujar_numeros_como_texto(INSIGHTS, ("spend", "impressions", "clicks"))
    assert all(isinstance(r["spend"], str) for r in sujos)
    assert all(isinstance(r["impressions"], str) for r in sujos)
    assert sujos[0]["spend"] == "1234.56"
    assert sujos[0]["campaign_id"] == INSIGHTS[0]["campaign_id"]  # não mexe no resto


def test_numeros_como_texto_nao_muda_o_original():
    """Sujeira é função PURA. Mutar a entrada faria a ordem das injeções
    importar, e o resultado dependeria de quem rodou antes."""
    from dados_sinteticos.exportar import sujar_numeros_como_texto

    antes = INSIGHTS[0]["spend"]
    sujar_numeros_como_texto(INSIGHTS, ("spend",))
    assert INSIGHTS[0]["spend"] == antes


def test_utm_sai_em_caixas_diferentes():
    """Cinco caixas conviverem no mesmo arquivo é o que obriga o staging a
    normalizar. Uma caixa só e a normalização vira código sem propósito."""
    import numpy as np

    from dados_sinteticos.exportar import sujar_caixa_utm

    sujos = sujar_caixa_utm(CONTATOS, ("utm_source",), np.random.default_rng(7))
    assert len({r["utm_source"] for r in sujos}) >= 3


def test_caixa_utm_normalizada_volta_ao_original():
    """A sujeira é de APRESENTAÇÃO. Depois de `lower()` e `strip()`, tem que
    sobrar exatamente o valor de origem — senão não é caixa, é valor trocado."""
    import numpy as np

    from dados_sinteticos.exportar import sujar_caixa_utm

    sujos = sujar_caixa_utm(CONTATOS, ("utm_source",), np.random.default_rng(7))
    normalizados = {r["utm_source"].strip().lower().replace("-", "_") for r in sujos}
    assert normalizados == {"facebook ads", "facebook_ads"} or normalizados == {"facebook_ads"}


def test_duplicar_contatos_respeita_a_fracao():
    """~3% (COMPLETUDE_BASE.contato_duplicado). A contagem devolvida vai para o
    gabarito: sem ela, o teste da Fase 2 não tem contra o que afirmar quantas
    linhas a deduplicação deveria remover."""
    import numpy as np

    from dados_sinteticos.exportar import duplicar_contatos

    sujos, quantidade = duplicar_contatos(CONTATOS, 0.03, np.random.default_rng(7))
    assert quantidade == len(sujos) - len(CONTATOS)
    assert 1 <= quantidade <= 6  # 3% de 100, com folga de arredondamento


def test_contato_duplicado_tem_mesmo_email_e_id_diferente():
    """É esta a forma da duplicata de CRM: a mesma pessoa preencheu dois
    formulários. E-mail igual, id diferente."""
    from collections import Counter

    import numpy as np

    from dados_sinteticos.exportar import duplicar_contatos

    sujos, _ = duplicar_contatos(CONTATOS, 0.05, np.random.default_rng(7))
    repetidos = [e for e, n in Counter(r["email"] for r in sujos).items() if n > 1]
    assert repetidos
    for email in repetidos:
        ids = {r["contact_id"] for r in sujos if r["email"] == email}
        assert len(ids) > 1, f"{email}: duplicata sem id novo"


def test_ids_continuam_unicos_apos_duplicacao():
    """`contact_id` é chave e continua única — o contrato (5.3) exige unicidade
    de id, e PROÍBE exigir unicidade de e-mail."""
    import numpy as np

    from dados_sinteticos.exportar import duplicar_contatos

    sujos, _ = duplicar_contatos(CONTATOS, 0.05, np.random.default_rng(7))
    ids = [r["contact_id"] for r in sujos]
    assert len(ids) == len(set(ids))


def test_reentrega_duplica_exatamente_um_dia():
    """Um dia de uma campanha reentregue pela API. Se a ingestão somar sem
    deduplicar, o custo daquele dia dobra e a R1 dispara num problema que não
    existe."""
    import numpy as np

    from dados_sinteticos.exportar import reentregar_um_dia

    sujos, chave = reentregar_um_dia(INSIGHTS, np.random.default_rng(7))
    assert len(sujos) == len(INSIGHTS) + 1
    assert chave


def test_dia_reentregue_e_copia_exata():
    """Duplicata EXATA (todos os campos iguais) é reentrega e pode ser
    deduplicada sem perda. Duplicata de CHAVE com `spend` diferente seria
    contradição, e aí o contrato manda reprovar o build."""
    from collections import Counter

    import numpy as np

    from dados_sinteticos.exportar import reentregar_um_dia

    sujos, _ = reentregar_um_dia(INSIGHTS, np.random.default_rng(7))
    assinaturas = Counter(tuple(sorted(r.items())) for r in sujos)
    assert max(assinaturas.values()) == 2, "a cópia não é idêntica"


def test_orfaniza_exatamente_uma_campanha():
    """Campanha que aparece no CRM e não nos insights. Acontece quando o
    vendedor digita a origem à mão ou a campanha foi excluída da conta."""
    import numpy as np

    from dados_sinteticos.exportar import orfanizar_uma_campanha

    conhecidas = {r["campaign_id"] for r in INSIGHTS}
    sujos, orfa = orfanizar_uma_campanha(NEGOCIOS, np.random.default_rng(7))
    vistas = {r["campaign_source"] for r in sujos if r["campaign_source"]}
    assert orfa not in conhecidas
    assert len(vistas - conhecidas) == 1


# ===========================================================================
# Semente da sujeira
# ===========================================================================
def test_semente_da_sujeira_nao_colide_com_a_do_gerador():
    """`SeedSequence(s).spawn(2)[1]` é o MESMO fluxo de `spawn(12)[1]`, que o
    gerador usa para a conta nº 2. A sujeira precisa de entropia própria."""
    from dados_sinteticos.exportar import SEMENTE_SUJEIRA_PADRAO

    assert SEMENTE_SUJEIRA_PADRAO != SEMENTE_PADRAO


# ===========================================================================
# Integração — a árvore que `make dados` produz
# ===========================================================================
@pytest.fixture(scope="session")
def exportado(normal, tmp_path_factory):
    """Uma exportação completa, reaproveitada pelos testes de integração."""
    from dados_sinteticos.exportar import exportar

    raiz = tmp_path_factory.mktemp("saida")
    gabarito = exportar(normal, raiz)
    return raiz, gabarito


def test_exporta_uma_pasta_por_conta(exportado):
    raiz, _ = exportado
    for conta in CONTAS_PADRAO:
        assert (raiz / "raw" / conta.id).is_dir(), conta.id


def test_cada_conta_tem_as_cinco_fontes(exportado):
    raiz, _ = exportado
    pasta = raiz / "raw" / CONTAS_PADRAO[0].id
    nomes = {p.name for p in pasta.iterdir()}
    assert any(n.startswith("meta_ads_insights_pagina_") for n in nomes)
    for esperado in (
        "crm_contatos.csv",
        "crm_negocios.csv",
        "crm_atividades.csv",
        "financeiro_margens.csv",
    ):
        assert esperado in nomes, esperado


def test_gabarito_vai_para_avaliacao(exportado):
    raiz, _ = exportado
    assert (raiz / "avaliacao" / "gabarito_contas.json").is_file()


def test_gabarito_nunca_aparece_em_raw(exportado):
    """A regra mais importante do projeto: o pipeline não pode enxergar a
    resposta. Um gabarito dentro de raw/ invalidaria toda a medição."""
    raiz, _ = exportado
    achados = list((raiz / "raw").rglob("*gabarito*"))
    assert achados == [], achados


def test_gabarito_registra_a_sujeira_em_contagem(exportado):
    """Contagem, não lista de ids: a Fase 2 precisa saber QUANTAS linhas a
    deduplicação deve remover, sem receber quais são."""
    _, gabarito = exportado
    conta = gabarito["contas"][CONTAS_PADRAO[0].id]
    assert "sujeira" in conta
    assert conta["sujeira"]["contatos_duplicados"] >= 0


def test_amostras_sao_curtas_e_versionaveis(exportado):
    """A vitrine de quem abre o GitHub e não vai clonar nada. Gerada pelo mesmo
    código que escreve raw/, para não apodrecer."""
    raiz, _ = exportado
    amostras = list((raiz / "docs" / "amostras").iterdir())
    assert amostras
    assert all(p.stat().st_size < 20_000 for p in amostras)


def test_exportacao_e_reprodutivel(normal, tmp_path):
    """Mesma entrada e mesma semente de sujeira: arquivos byte a byte iguais.
    É o critério de saída da etapa, e o que faz `make dados` valer."""
    from dados_sinteticos.exportar import exportar

    a, b = tmp_path / "a", tmp_path / "b"
    exportar(normal, a)
    exportar(normal, b)
    for arquivo in sorted((a / "raw").rglob("*")):
        if arquivo.is_file():
            espelho = b / arquivo.relative_to(a)
            assert arquivo.read_bytes() == espelho.read_bytes(), arquivo.name


def test_csv_do_crm_pode_sair_com_aspas(tmp_path):
    """O export do CRM traz campos entre aspas (contrato, 5.2); o financeiro
    nao (5.5). Por isso e parametro e nao default."""
    from dados_sinteticos.exportar import _escrever_csv

    caminho = tmp_path / "crm_contatos.csv"
    _escrever_csv([{"nome": "Pessoa 1"}], caminho, citar=True)
    assert caminho.read_text(encoding="utf-8").startswith('"nome"')
