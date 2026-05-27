"""PyTorch 기반 딥러닝(Transformer/GRU) 시계열 모델."""

import torch
import torch.nn as nn
import pandas as pd
import numpy as np
from typing import Tuple

class SimpleTimeSeriesTransformer(nn.Module):
    """딥러닝 기반 시계열 예측을 위한 간이 Transformer 모델."""
    def __init__(self, input_dim=24, hidden_dim=64, n_heads=4, n_layers=2):
        super(SimpleTimeSeriesTransformer, self).__init__()
        self.embedding = nn.Linear(input_dim, hidden_dim)
        
        encoder_layer = nn.TransformerEncoderLayer(d_model=hidden_dim, nhead=n_heads, batch_first=True)
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)
        
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        # x shape: [batch, seq_len, input_dim]
        x = self.embedding(x)
        x = self.transformer(x)
        # 마지막 타임스텝의 결과만 사용
        out = self.fc(x[:, -1, :])
        return self.sigmoid(out)

def prepare_deep_training_data(df: pd.DataFrame, seq_len=30) -> Tuple[torch.Tensor, torch.Tensor]:
    """시계열 윈도우 데이터 생성."""
    # 단순화를 위한 예시 코드
    data = df.select_dtypes(include=[np.number]).values
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i+seq_len])
        y.append(data[i+seq_len, 0]) # 종가 기준 타겟 (가정)
    return torch.tensor(X, dtype=torch.float32), torch.tensor(y, dtype=torch.float32)

def train_deep_model(X, y):
    """간이 학습 루프."""
    model = SimpleTimeSeriesTransformer()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.BCELoss()
    
    model.train()
    # 1 epoch만 예시 실행
    optimizer.zero_grad()
    outputs = model(X)
    loss = criterion(outputs.squeeze(), (y > 0).float())
    loss.backward()
    optimizer.step()
    
    torch.save(model.state_dict(), "models/transformer_model.pth")
    return model
