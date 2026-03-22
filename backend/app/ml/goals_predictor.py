"""
Dixon-Coles Poisson + Random Forest for total goals and per-team O/U.
"""

import os
import numpy as np
import pandas as pd
import joblib
from scipy.stats import poisson
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
from loguru import logger

from app.ml.features import FEATURE_COLUMNS, FEATURE_DEFAULTS, build_feature_matrix
from app.core.config import get_settings

settings = get_settings()


class DixonColesModel:

    def __init__(self):
        self.attack = {}
        self.defense = {}
        self.home_advantage = 0.25
        self.rho = -0.13

    def fit(self, df: pd.DataFrame, decay_rate: float = 0.005, max_seasons: int = 3):
        df = df.dropna(subset=["home_goals", "away_goals"]).copy()
        if df.empty:
            return

        if "season" in df.columns and max_seasons:
            recent_seasons = sorted(df["season"].unique())[-max_seasons:]
            df = df[df["season"].isin(recent_seasons)]

        teams = list(set(df["home_team"].tolist() + df["away_team"].tolist()))
        team_idx = {t: i for i, t in enumerate(teams)}
        n_teams = len(teams)

        df["match_date"] = pd.to_datetime(df["match_date"])
        max_date = df["match_date"].max()
        weights = df["match_date"].apply(lambda d: np.exp(-decay_rate * (max_date - d).days)).values
        home_goals = df["home_goals"].astype(int).values
        away_goals = df["away_goals"].astype(int).values
        home_idx = df["home_team"].map(team_idx).values
        away_idx = df["away_team"].map(team_idx).values

        x0 = np.concatenate([np.zeros(n_teams), np.zeros(n_teams), [0.25], [-0.13]])

        def neg_ll(params):
            att = params[:n_teams]
            dfn = params[n_teams:2 * n_teams]
            ha = params[2 * n_teams]
            rho = params[2 * n_teams + 1]

            lh = np.exp(att[home_idx] + dfn[away_idx] + ha)
            la = np.exp(att[away_idx] + dfn[home_idx])
            lh = np.clip(lh, 0.01, 10)
            la = np.clip(la, 0.01, 10)

            p = poisson.pmf(home_goals, lh) * poisson.pmf(away_goals, la)
            tau = np.ones(len(df))
            m00 = (home_goals == 0) & (away_goals == 0)
            m01 = (home_goals == 0) & (away_goals == 1)
            m10 = (home_goals == 1) & (away_goals == 0)
            m11 = (home_goals == 1) & (away_goals == 1)
            tau[m00] = 1 - lh[m00] * la[m00] * rho
            tau[m01] = 1 + lh[m01] * rho
            tau[m10] = 1 + la[m10] * rho
            tau[m11] = 1 - rho
            p = p * tau

            ll = np.sum(weights * np.log(np.clip(p, 1e-10, None)))
            penalty = 100 * (np.sum(att) ** 2)
            return -ll + penalty

        result = minimize(neg_ll, x0, method="L-BFGS-B", options={"maxiter": 500})
        if result.success:
            for team, idx in team_idx.items():
                self.attack[team] = result.x[idx]
                self.defense[team] = result.x[n_teams + idx]
            self.home_advantage = result.x[2 * n_teams]
            self.rho = result.x[2 * n_teams + 1]
            logger.info(f"Dixon-Coles fitted: HA={self.home_advantage:.3f}, rho={self.rho:.3f}, {n_teams} teams")
        else:
            logger.warning(f"Dixon-Coles did not converge: {result.message}")

    def predict_lambdas(self, home_team: str, away_team: str) -> tuple[float, float]:
        att_h = self.attack.get(home_team, 0)
        def_a = self.defense.get(away_team, 0)
        att_a = self.attack.get(away_team, 0)
        def_h = self.defense.get(home_team, 0)
        lh = np.exp(att_h + def_a + self.home_advantage)
        la = np.exp(att_a + def_h)
        return float(lh), float(la)

    def predict_score_matrix(self, home_team: str, away_team: str, max_goals: int = 8) -> np.ndarray:
        lh, la = self.predict_lambdas(home_team, away_team)
        h_range = poisson.pmf(np.arange(max_goals + 1), lh)
        a_range = poisson.pmf(np.arange(max_goals + 1), la)
        matrix = np.outer(h_range, a_range)

        # Dixon-Coles correction on low scores
        rho = self.rho
        matrix[0, 0] *= (1 - lh * la * rho)
        matrix[0, 1] *= (1 + lh * rho)
        matrix[1, 0] *= (1 + la * rho)
        matrix[1, 1] *= (1 - rho)

        return matrix / matrix.sum()

    def predict_full(self, home_team: str, away_team: str) -> dict:
        matrix = self.predict_score_matrix(home_team, away_team)
        n = matrix.shape[0]
        lh, la = self.predict_lambdas(home_team, away_team)

        prob_home = sum(matrix[i][j] for i in range(n) for j in range(n) if i > j)
        prob_draw = sum(matrix[i][i] for i in range(n))
        prob_away = sum(matrix[i][j] for i in range(n) for j in range(n) if i < j)

        result = {
            "prob_home": float(prob_home),
            "prob_draw": float(prob_draw),
            "prob_away": float(prob_away),
            "expected_total_goals": float(lh + la),
            "home_lambda": float(lh),
            "away_lambda": float(la),
        }

        # Total O/U from score matrix
        for threshold in [0.5, 1.5, 2.5, 3.5]:
            over = sum(matrix[i][j] for i in range(n) for j in range(n) if i + j > threshold)
            result[f"over_{threshold}"] = float(over)
            result[f"under_{threshold}"] = float(1 - over)

        # Per-team O/U from individual Poisson distributions
        for prefix, lam in [("home", lh), ("away", la)]:
            for threshold in [0.5, 1.5, 2.5]:
                k = int(threshold)
                over = 1.0 - float(poisson.cdf(k, lam))
                result[f"{prefix}_over_{threshold}"] = over
                result[f"{prefix}_under_{threshold}"] = 1.0 - over

        return result


class GoalsPredictor:

    def __init__(self):
        self.dc_model = DixonColesModel()
        self.rf_model = None
        self.is_fitted = False

    def train(
        self,
        matches_df: pd.DataFrame,
        player_df: pd.DataFrame | None = None,
        data_dir: "Path | None" = None,
    ) -> dict:
        logger.info("Training Dixon-Coles model...")
        finished = matches_df.dropna(subset=["home_goals", "away_goals"])
        self.dc_model.fit(finished)

        logger.info("Building features for RF goals model...")
        df = build_feature_matrix(matches_df, player_df=player_df, data_dir=data_dir)
        df = df.dropna(subset=["total_goals"])

        X = df[FEATURE_COLUMNS].fillna(FEATURE_DEFAULTS)
        y = df["total_goals"]

        tscv = TimeSeriesSplit(n_splits=5)
        train_idx, val_idx = list(tscv.split(X))[-1]
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        self.rf_model = RandomForestRegressor(
            n_estimators=300, max_depth=8, min_samples_leaf=10,
            random_state=42, n_jobs=-1,
        )
        self.rf_model.fit(X_train, y_train)
        self.is_fitted = True

        rf_preds = self.rf_model.predict(X_val)
        metrics = {
            "mae": round(float(mean_absolute_error(y_val, rf_preds)), 4),
            "val_size": len(y_val),
        }
        logger.info(f"Goals metrics: {metrics}")
        return metrics

    def predict(self, home_team: str, away_team: str, features: dict | None = None) -> dict:
        result = self.dc_model.predict_full(home_team, away_team)

        if features and self.rf_model is not None:
            X = pd.DataFrame([features])[FEATURE_COLUMNS].fillna(FEATURE_DEFAULTS)
            rf_total = float(self.rf_model.predict(X)[0])
            blended = 0.6 * result["expected_total_goals"] + 0.4 * rf_total

            ratio = blended / max(result["expected_total_goals"], 0.01)
            lh = result["home_lambda"] * ratio
            la = result["away_lambda"] * ratio

            # Recompute O/U with blended lambdas
            for threshold in [0.5, 1.5, 2.5, 3.5]:
                over = 1.0 - float(poisson.cdf(int(threshold), lh + la))
                result[f"over_{threshold}"] = over
                result[f"under_{threshold}"] = 1.0 - over

            for prefix, lam in [("home", lh), ("away", la)]:
                for threshold in [0.5, 1.5, 2.5]:
                    over = 1.0 - float(poisson.cdf(int(threshold), lam))
                    result[f"{prefix}_over_{threshold}"] = over
                    result[f"{prefix}_under_{threshold}"] = 1.0 - over

            result["expected_total_goals"] = blended
            result["home_lambda"] = float(lh)
            result["away_lambda"] = float(la)

        return result

    def save(self, path: str | None = None):
        d = path or settings.model_dir
        os.makedirs(d, exist_ok=True)
        joblib.dump(self.dc_model, os.path.join(d, "dixon_coles.pkl"))
        if self.rf_model:
            joblib.dump(self.rf_model, os.path.join(d, "rf_goals.pkl"))
        logger.info(f"Goals models saved to {d}")

    def load(self, path: str | None = None):
        d = path or settings.model_dir
        dc_path = os.path.join(d, "dixon_coles.pkl")
        rf_path = os.path.join(d, "rf_goals.pkl")
        if os.path.exists(dc_path):
            self.dc_model = joblib.load(dc_path)
        if os.path.exists(rf_path):
            self.rf_model = joblib.load(rf_path)
            self.is_fitted = True
        logger.info("Goals models loaded")
