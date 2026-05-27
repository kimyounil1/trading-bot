"""강화학습(RL) 기반 동적 포트폴리오 비중 조절 엔진."""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
from stable_baselines3 import PPO
from typing import Dict, List

class TradingEnv(gym.Env):
    """포트폴리오 비중 조절을 위한 강화학습 환경."""
    def __init__(self, ticker_data: pd.DataFrame, initial_balance=10000):
        super(TradingEnv, self).__init__()
        self.df = ticker_data
        self.initial_balance = initial_balance
        
        # Action: 각 종목에 대한 비중 조절 (-1 ~ 1 사이의 연속값, 나중에 Softmax 등으로 정규화)
        # 단순화를 위해 '현금 비중 조절'만 학습 (0=현금 100%, 1=주식 100%)
        self.action_space = spaces.Box(low=0, high=1, shape=(1,), dtype=np.float32)
        
        # Observation: MA ratio, RSI, AI Score 등 주요 지표 (현재 행 기준)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32)
        
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.balance = self.initial_balance
        self.shares_held = 0
        return self._get_observation(), {}

    def _get_observation(self):
        # 실제 데이터에서 피처 추출 (예시로 0으로 채움)
        obs = np.zeros((10,), dtype=np.float32)
        return obs

    def step(self, action):
        # Action 적용 (비중 결정)
        target_equity_pct = action[0]
        
        # 수익률 계산 및 보상(Reward) 부여
        current_price = self.df.iloc[self.current_step]['close']
        next_price = self.df.iloc[self.current_step + 1]['close'] if self.current_step < len(self.df)-1 else current_price
        
        price_return = (next_price - current_price) / current_price
        reward = target_equity_pct * price_return # 비중에 따른 수익이 곧 보상
        
        self.current_step += 1
        done = self.current_step >= len(self.df) - 1
        
        return self._get_observation(), float(reward), done, False, {}

def train_rl_agent(ticker_data: pd.DataFrame):
    """PPO 알고리즘을 사용하여 비중 조절 에이전트를 학습시킨다."""
    env = TradingEnv(ticker_data)
    model = PPO("MlpPolicy", env, verbose=1)
    model.learn(total_timesteps=1000)
    model.save("models/rl_portfolio_agent")
    return model

def get_rl_allocation_weight(model, current_obs) -> float:
    """학습된 에이전트로부터 현재 시장 상황에 맞는 최적 비중을 제안받는다."""
    action, _states = model.predict(current_obs)
    return float(action[0])
