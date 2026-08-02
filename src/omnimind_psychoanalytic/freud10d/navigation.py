"""
Módulo de Navegação no Espaço de Estados 10D (Attractor Navigator).
===================================================================
Implementa a identificação e navegação de regimes clínicos com base em
distâncias geométricas a centróides ideais (atratores).
"""

from __future__ import annotations

import numpy as np
import torch
from typing import Dict, Any, Tuple, List
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# CENTRÓIDES DOS ATRATORES CLÍNICOS NO ESPAÇO 10D
# ==============================================================================
# Dimensões: [phi, psi, omega, theta, upsilon, xi, zeta, eta, kappa, lambda_]
# index:     [ 0 ,  1 ,   2  ,   3  ,    4   , 5 ,  6  ,  7 ,   8  ,    9   ]
ATTRACTOR_CENTROIDS = {
    "ESTAVEL_REPARACAO": [
        0.3,  # phi: percepção moderada
        0.5,  # psi: memória integrada
        0.7,  # omega: consciência ativa
        0.5,  # theta: pré-consciente equilibrado
        0.2,  # upsilon: inconsciente calmo
        0.2,  # xi: pulsão/id atenuada
        0.8,  # zeta: ego integrador forte
        0.2,  # eta: superego benevolente
        0.3,  # kappa: transferência positiva/estável
        0.8,  # lambda: sublimação ativa
    ],
    "COLAPSO_DISSOCIACAO": [
        0.7,  # phi: sobrecarga perceptual
        0.7,  # psi: memória fragmentada
        0.2,  # omega: consciência diminuída
        0.2,  # theta: pré-consciente inoperante
        0.8,  # upsilon: inconsciente inundado
        0.9,  # xi: pulsão/id descontrolada
        0.1,  # zeta: ego cindido/desintegrado
        0.9,  # eta: superego punitivo/censor
        0.8,  # kappa: transferência regressiva
        0.1,  # lambda: sublimação inibida
    ],
    "POSICAO_EP": [
        0.6,  # phi: atenção vigilante
        0.4,  # psi: memória polarizada
        0.3,  # omega: consciência ansiosa
        0.3,  # theta: pré-consciente cindido
        0.6,  # upsilon: inconsciente persecutório
        0.8,  # xi: agressão/id ativo
        0.3,  # zeta: ego polarizador fraco
        0.7,  # eta: superego perseguidor
        0.8,  # kappa: transferência cindida (idealização/desvalorização)
        0.2,  # lambda: sublimação fraca
    ],
    "POSICAO_D": [
        0.4,  # phi: percepção realista
        0.7,  # psi: memória integrada de objetos
        0.5,  # omega: consciência reflexiva
        0.5,  # theta: pré-consciente integrado
        0.4,  # upsilon: inconsciente metabolizado
        0.3,  # xi: agressão mitigada
        0.7,  # zeta: ego mediador integrado
        0.4,  # eta: superego flexível
        0.4,  # kappa: transferência integrada/realista
        0.6,  # lambda: sublimação reparativa
    ]
}


class AttractorRegistry:
    """
    Catálogo de atratores clínicos fixos e dinâmicos no espaço de estados do OmniMind.
    """
    def __init__(self, device: str = "cpu", dtype: torch.dtype = torch.float32):
        self.device = torch.device(device)
        self.dtype = dtype
        self.centroids: Dict[str, torch.Tensor] = {}
        for name, vec in ATTRACTOR_CENTROIDS.items():
            self.centroids[name] = torch.tensor(vec, device=self.device, dtype=self.dtype)

    def get_centroid(self, name: str) -> torch.Tensor:
        return self.centroids[name]

    def get_distances(self, state: torch.Tensor) -> Dict[str, float]:
        """Calcula a distância euclidiana do estado atual para todos os centróides."""
        # Alinha dimensões do tensor
        state = state.to(device=self.device, dtype=self.dtype).view(-1)
        distances = {}
        for name, centroid in self.centroids.items():
            dist = float(torch.linalg.norm(state - centroid).item())
            distances[name] = dist
        return distances


class TransitionGraph:
    """
    Grafo de recorrência e memória de transições entre regimes.
    Registra padrões e frequências de migração de estados.
    """
    def __init__(self):
        self.transitions: Dict[Tuple[str, str], int] = {}
        self.last_regime: str | None = None

    def record_transition(self, current_regime: str) -> None:
        """Registra a mudança de regime na memória do grafo."""
        if self.last_regime is not None and self.last_regime != current_regime:
            key = (self.last_regime, current_regime)
            self.transitions[key] = self.transitions.get(key, 0) + 1
        self.last_regime = current_regime

    def get_transition_probabilities(self, from_regime: str) -> Dict[str, float]:
        """Calcula probabilidades empíricas de transição a partir de um regime."""
        outgoings = {k[1]: v for k, v in self.transitions.items() if k[0] == from_regime}
        total = sum(outgoings.values())
        if total == 0:
            return {}
        return {dest: count / total for dest, count in outgoings.items()}

    def to_dict(self) -> List[Dict[str, Any]]:
        """Exporta o grafo em formato legível para serialização."""
        return [
            {"from": k[0], "to": k[1], "count": v}
            for k, v in self.transitions.items()
        ]


class AttractorNavigator:
    """
    Interpretador e navegador de regimes clínicos do aparelho psíquico.
    Acompanha trajetórias, distâncias aos atratores e prevê transições de fase.
    """
    def __init__(self, history_len: int = 5, device: str = "cpu", dtype: torch.dtype = torch.float32):
        self.registry = AttractorRegistry(device=device, dtype=dtype)
        self.graph = TransitionGraph()
        self.history_len = history_len
        self.trajectory_history: List[torch.Tensor] = []

    def navigate(self, state_vector: torch.Tensor) -> Dict[str, Any]:
        """
        Navega no espaço de estados 10D:
        - Determina o atrator mais próximo.
        - Estima o regime e sua confiança.
        - Identifica a tendência da trajetória para estimar candidatos a transições.
        """
        state = state_vector.detach().clone().to(device=self.registry.device, dtype=self.registry.dtype).view(-1)
        self.trajectory_history.append(state)
        if len(self.trajectory_history) > self.history_len:
            self.trajectory_history.pop(0)

        # 1. Distâncias
        distances = self.registry.get_distances(state)
        sorted_attractors = sorted(distances.items(), key=lambda x: x[1])
        
        current_attractor = sorted_attractors[0][0]
        min_dist = sorted_attractors[0][1]
        
        # 2. Confiança do regime (escala exponencial invertida)
        regime_confidence = float(np.exp(-min_dist))
        
        # 3. Tendência de trajetória e candidato a transição
        transition_candidate = "NENHUM"
        if len(self.trajectory_history) >= 2:
            # Vetor direção do movimento (último - primeiro no histórico curto)
            direction = state - self.trajectory_history[0]
            
            # Queremos ver para qual atrator a distância está diminuindo de forma mais consistente
            max_reduction = 0.0
            for name, centroid in self.registry.centroids.items():
                if name == current_attractor:
                    continue
                # Se projetarmos a direção do movimento em direção ao centróide
                to_centroid = centroid - state
                proj = float(torch.dot(direction, to_centroid).item())
                if proj > max_reduction:
                    max_reduction = proj
                    transition_candidate = name

        # Registra transição se houver
        self.graph.record_transition(current_attractor)

        return {
            "current_attractor": current_attractor,
            "distance_to_attractor": min_dist,
            "regime_confidence": regime_confidence,
            "transition_candidate": transition_candidate,
            "all_distances": distances,
            "trajectory_depth": len(self.trajectory_history)
        }
