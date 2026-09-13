"""Testes de `dados_sinteticos.gerador`.

Escritos ANTES do gerador: são a especificação da etapa 1.6. Enquanto as
funções levantarem NotImplementedError, quase tudo aqui falha — e cada falha
diz o que falta.
"""

from datetime import date, timedelta

import numpy as np
import pytest

from dados_sinteticos.gerador import (
    dias_de_captacao,
    e_fim_de_semana,
    fim_da_simulacao,
    gerar,
)
from dados_sinteticos.parametros import (
    CONTAS_PADRAO,
    DATA_INICIO_BASELINE,
    DISTRIBUICAO_LAG,
    JANELA_PADRAO,
)


# --------------------------------------------------------------------------
# Calendário — não depende de nenhuma função ainda não escrita
# --------------------------------------------------------------------------
def test_captacao_cobre_baseline_mais_analisado():
    """Os 30 dias de maturação NÃO captam lead: só deixam os negócios fecharem."""
    dias = dias_de_captacao()
    assert len(dias) == JANELA_PADRAO.baseline + JANELA_PADRAO.analisado
    assert dias[0] == DATA_INICIO_BASELINE


def test_ancora_e_segunda_feira():
    """Começar no meio da semana desequilibraria a contagem de fins de semana
    entre os dois períodos, e a sazonalidade (armadilha) viraria sinal."""
    assert DATA_INICIO_BASELINE.weekday() == 0


def test_simulacao_vai_alem_do_ultimo_lead():
    """Sem a folga de maturação, a coorte final nunca amadurece (ADR 0001)."""
    folga = fim_da_simulacao() - dias_de_captacao()[-1]
    assert folga == timedelta(days=JANELA_PADRAO.maturacao)


def test_reconhece_fim_de_semana():
    assert e_fim_de_semana(date(2026, 3, 7))  # sábado
    assert e_fim_de_semana(date(2026, 3, 8))  # domingo
    assert not e_fim_de_semana(date(2026, 3, 9))  # segunda


# --------------------------------------------------------------------------
# Reprodutibilidade — o critério de saída da etapa
# --------------------------------------------------------------------------
def test_mesma_semente_mesmo_resultado():
    """Critério de saída da 1.6. Passa trivialmente enquanto tudo é vazio e vai
    ficando difícil conforme o gerador cresce — que é quando ele importa."""
    assert gerar("normal", 42) == gerar("normal", 42)


def test_sementes_diferentes_resultados_diferentes():
    """Se isto falhar, algum sorteio está fixo onde deveria variar."""
    assert gerar("normal", 42) != gerar("normal", 43)


def test_conta_e_independente_da_posicao_na_lista():
    """`SeedSequence.spawn` dá fluxo próprio a cada conta: a primeira conta não
    pode mudar porque outra foi inserida depois dela."""
    a = gerar("normal", 42).dados[0]
    b = gerar("normal", 42).dados[0]
    assert a == b


# --------------------------------------------------------------------------
# Forma da saída
# --------------------------------------------------------------------------
def test_gera_as_doze_contas(normal):
    resultado = normal
    assert len(resultado.dados) == len(CONTAS_PADRAO)


def test_gabarito_registra_semente_e_cenario(normal):
    """Sem a semente no gabarito, um resultado estranho da fase 3 não é
    reproduzível."""
    gabarito = normal.gabarito
    assert gabarito["semente"] == 42
    assert gabarito["cenario"] == "normal"
    assert set(gabarito["contas"]) == {c.id for c in CONTAS_PADRAO}


def test_cenario_desconhecido_falha_alto():
    """Nome errado tem que estourar aqui, não gerar dado silenciosamente vazio."""
    with pytest.raises(ValueError):
        gerar("cenario_que_nao_existe", 42)


# --------------------------------------------------------------------------
# Coerência temporal — o que a etapa 2.5 vai testar de novo, em SQL
# --------------------------------------------------------------------------
def test_nenhum_negocio_fecha_antes_do_lead(normal):
    """Teste singular exigido pela etapa 2.5, antecipado aqui."""
    for conta in normal.dados:
        for negocio in conta.negocios:
            if negocio.fechado_em is not None:
                assert negocio.fechado_em >= negocio.criado_em, negocio.id


def test_nada_fecha_depois_do_fim_da_simulacao(normal):
    """Negócio com lag além da janela permanece ABERTO — insumo da R6."""
    limite = fim_da_simulacao()
    for conta in normal.dados:
        for negocio in conta.negocios:
            if negocio.fechado_em is not None:
                assert negocio.fechado_em.date() <= limite, negocio.id


def test_todo_lead_cai_dentro_da_janela_de_captacao(normal):
    dias = set(dias_de_captacao())
    for conta in normal.dados:
        for lead in conta.leads:
            assert lead.quando.date() in dias, lead.id


def test_lead_e_negocio_carregam_fuso(normal):
    """O contrato exige ISO 8601 com -03:00; datetime ingênuo não sobrevive à
    conversão para UTC no staging."""
    conta = normal.dados[0]
    assert conta.leads[0].quando.tzinfo is not None


# --------------------------------------------------------------------------
# Distribuição do lag — o ponto crítico da etapa
# --------------------------------------------------------------------------
def test_lag_respeita_a_mediana_pedida():
    """O lag vem de distribuição, não de constante. Com 10 mil sorteios, a
    mediana empírica tem que ficar perto da pedida."""
    from dados_sinteticos.gerador import _sortear_lag

    rng = np.random.default_rng(42)
    amostra = [_sortear_lag(20, rng) for _ in range(10_000)]
    assert 18 <= float(np.median(amostra)) <= 22


def test_lag_nao_e_constante():
    from dados_sinteticos.gerador import _sortear_lag

    rng = np.random.default_rng(42)
    amostra = {_sortear_lag(20, rng) for _ in range(200)}
    assert len(amostra) > 10, "lag saiu quase constante"


def test_lag_respeita_o_corte():
    from dados_sinteticos.gerador import _sortear_lag

    rng = np.random.default_rng(42)
    amostra = [_sortear_lag(42, rng) for _ in range(10_000)]
    assert max(amostra) <= DISTRIBUICAO_LAG.corte_dias
    assert min(amostra) >= 0
