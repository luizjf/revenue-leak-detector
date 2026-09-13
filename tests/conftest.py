"""Fixtures compartilhadas."""

import pytest

from dados_sinteticos.gerador import gerar


@pytest.fixture(scope="session")
def normal():
    """Uma execução de `gerar("normal", 42)` reaproveitada pela sessão.

    Custa ~5 s. Testes que apenas INSPECIONAM a saída usam esta fixture; os
    que verificam reprodutibilidade chamam `gerar()` por conta própria —
    reaproveitar ali tornaria a comparação trivialmente verdadeira e o teste
    deixaria de testar.
    """
    return gerar("normal", 42)
