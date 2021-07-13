import torch
import torch.nn.functional as F
import GCL.augmentors as A

from typing import Optional, Tuple
from torch_geometric.nn import GCNConv


class L2L(torch.nn.Module):
    def __init__(self, encoder: torch.nn.Module,
                 augmentor: Tuple[A.Augmentor, A.Augmentor],
                 loss,
                 hidden_dim: int, proj_dim: int):
        super(L2L, self).__init__()
        self.encoder = encoder
        self.augmentor = augmentor
        self.loss = loss

        self.fc1 = torch.nn.Linear(hidden_dim, proj_dim)
        self.fc2 = torch.nn.Linear(proj_dim, hidden_dim)

        self.num_hidden = hidden_dim

    def forward(self, x: torch.Tensor,
                edge_index: torch.Tensor, edge_weight: Optional[torch.Tensor] = None)\
            -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        aug1, aug2 = self.augmentor
        x1, edge_index1, edge_weight1 = aug1(x, edge_index, edge_weight)
        x2, edge_index2, edge_weight2 = aug2(x, edge_index, edge_weight)

        z = self.encoder(x, edge_index, edge_weight)
        z1 = self.encoder(x1, edge_index1, edge_weight1)
        z2 = self.encoder(x2, edge_index2, edge_weight2)

        return z, z1, z2

    def projection(self, z: torch.Tensor) -> torch.Tensor:
        z = F.elu(self.fc1(z))
        return self.fc2(z)


class NodeEncoder(torch.nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, activation, num_layers: int, batch_norm: bool = False):
        super(NodeEncoder, self).__init__()
        self.activation = activation()
        self.layers = torch.nn.ModuleList()
        self.batch_norms = torch.nn.ModuleList() if batch_norm else None
        self.layers.append(GCNConv(input_dim, hidden_dim, cached=False))

        for _ in range(num_layers - 1):
            # add batch norm layer if batch norm is used
            if self.batch_norms is not None:
                self.batch_norms.append(torch.nn.BatchNorm1d(hidden_dim))
            self.layers.append(GCNConv(hidden_dim, hidden_dim, cached=False))

    def forward(self, x, edge_index, edge_weight=None):
        z = x
        num_layers = len(self.layers)
        for i, conv in enumerate(self.layers):
            z = conv(z, edge_index, edge_weight)
            z = self.activation(z)
            if self.batch_norms is not None and i != num_layers - 1:
                z = self.batch_norms[i](z)
        return z
