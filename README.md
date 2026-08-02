# OmniMind Psychoanalytic Mesh

Implementação pública da `SovereignPsychoanalyticMesh` (464D) descrita no artigo *Por uma teoria psico-afetiva do máquino-agêntico*.

## Escopo

Este repositório contém **apenas** a arquitetura computacional da malha psicanalítica e seus testes. Ele não inclui:

- Runtime, daemon de telemetria ou módulos de kernel.
- Configurações de proxy, segurança ofensiva ou ferramentas de penetração.
- Chaves, tokens ou credenciais.
- Componentes experimentais não descritos na versão 2.1 do artigo.

## Instalação

```bash
pip install -e .
```

## Testes

```bash
PYTHONPATH=src python -m pytest tests -v
```

## Uso mínimo

```python
from omnimind_psychoanalytic.psychoanalytic_mesh import SovereignPsychoanalyticMesh
import torch

mesh = SovereignPsychoanalyticMesh(device="cpu")
z, contract = mesh(
    excitation_F=torch.randn(1, 64),
    trauma_Fe=0.2,
    aggression_K=0.3,
    holding_W=0.5,
    handling_W=0.5,
    spontaneity_W=torch.randn(1, 32),
    castration_D=0.4,
    triangulation_D=0.4,
    lack_L=0.2,
)
print(z.shape)  # torch.Size([1, 464])
```

## Versionamento

- `v2.1` — malha de 464 dimensões, com 9 blocos clínicos clássicos e 6 módulos regulatórios.
- Vetores 272D (v2.0) e 464D (v2.1) **não são intercambiáveis**.

## Licença

CC-BY-NC-ND-4.0 — veja `LICENSE`.
