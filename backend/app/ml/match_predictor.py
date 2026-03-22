"""1X2 Match Outcome Predictor -- XGBoost + LightGBM + CatBoost ensemble with calibration."""

import os
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import log_loss, accuracy_score
from sklearn.isotonic import IsotonicRegression
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from loguru import logger

from app.ml.features import FEATURE_COLUMNS, FEATURE_DEFAULTS, build_feature_matrix
from app.core.config import get_settings

settings = get_settings()


class MatchPredictor:

    def __init__(self):
        self.xgb_model = None
        self.lgbm_model = None
        self.catboost_model = None
        self.calibrators = None
        self.is_fitted = False

    def train(
        self,
        matches_df: pd.DataFrame,
        player_df: pd.DataFrame | None = None,
        data_dir: Path | None = None,
        **feature_kwargs,
    ) -> dict:
        logger.info("Building feature matrix...")
        df = build_feature_matrix(matches_df, player_df=player_df, data_dir=data_dir, **feature_kwargs)
        df = df.dropna(subset=["result_1x2"])

        X = df[FEATURE_COLUMNS].fillna(FEATURE_DEFAULTS)
        y = df["result_1x2"].astype(int)

        tscv = TimeSeriesSplit(n_splits=5)
        train_idx, val_idx = list(tscv.split(X))[-1]
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        logger.info(f"Training on {len(X_train)} matches, validating on {len(X_val)}")

        self.xgb_model = XGBClassifier(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            reg_alpha=0.1, reg_lambda=1.0,
            objective="multi:softprob", num_class=3,
            eval_metric="mlogloss", early_stopping_rounds=50,
            random_state=42, verbosity=0,
        )
        self.xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        self.lgbm_model = LGBMClassifier(
            n_estimators=500, max_depth=6, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=5,
            reg_alpha=0.1, reg_lambda=1.0,
            objective="multiclass", num_class=3,
            metric="multi_logloss", random_state=42, verbose=-1,
        )
        self.lgbm_model.fit(X_train, y_train, eval_set=[(X_val, y_val)])

        self.catboost_model = CatBoostClassifier(
            iterations=500, depth=6, learning_rate=0.05,
            l2_leaf_reg=3.0, bootstrap_type="MVS", subsample=0.8,
            loss_function="MultiClass", classes_count=3,
            eval_metric="MultiClass", random_seed=42,
            verbose=0, early_stopping_rounds=50,
        )
        self.catboost_model.fit(X_train, y_train, eval_set=(X_val, y_val))

        self.is_fitted = True

        # Calibrate on validation set
        raw_probs = self._raw_ensemble(X_val)
        self.calibrators = []
        for cls in range(3):
            cal = IsotonicRegression(out_of_bounds="clip")
            binary_target = (y_val == cls).astype(float)
            cal.fit(raw_probs[:, cls], binary_target)
            self.calibrators.append(cal)

        probs = self.predict_proba(X_val)
        preds = np.argmax(probs, axis=1)
        metrics = {
            "accuracy": round(float(accuracy_score(y_val, preds)), 4),
            "log_loss": round(float(log_loss(y_val, probs)), 4),
            "val_size": len(y_val),
        }
        logger.info(f"1X2 metrics: {metrics}")
        return metrics

    def _raw_ensemble(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        X_filled = X if isinstance(X, np.ndarray) else X[FEATURE_COLUMNS].fillna(FEATURE_DEFAULTS)
        xgb_p = self.xgb_model.predict_proba(X_filled)
        lgbm_p = self.lgbm_model.predict_proba(X_filled)
        cat_p = self.catboost_model.predict_proba(X_filled)
        return 0.35 * xgb_p + 0.30 * lgbm_p + 0.35 * cat_p

    def predict_proba(self, X: pd.DataFrame | np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not trained")
        raw = self._raw_ensemble(X)
        if self.calibrators:
            calibrated = np.column_stack([
                self.calibrators[cls].predict(raw[:, cls]) for cls in range(3)
            ])
            row_sums = calibrated.sum(axis=1, keepdims=True)
            row_sums = np.where(row_sums > 0, row_sums, 1.0)
            return calibrated / row_sums
        return raw / raw.sum(axis=1, keepdims=True)

    def predict_single(self, features: dict) -> dict:
        X = pd.DataFrame([features])[FEATURE_COLUMNS].fillna(FEATURE_DEFAULTS)
        probs = self.predict_proba(X)[0]
        return {"prob_home": float(probs[0]), "prob_draw": float(probs[1]), "prob_away": float(probs[2])}

    def save(self, path: str | None = None):
        d = path or settings.model_dir
        os.makedirs(d, exist_ok=True)
        joblib.dump(self.xgb_model, os.path.join(d, "xgb_1x2.pkl"))
        joblib.dump(self.lgbm_model, os.path.join(d, "lgbm_1x2.pkl"))
        joblib.dump(self.catboost_model, os.path.join(d, "catboost_1x2.pkl"))
        if self.calibrators:
            joblib.dump(self.calibrators, os.path.join(d, "calibrators_1x2.pkl"))
        logger.info(f"1X2 models saved to {d}")

    def load(self, path: str | None = None):
        d = path or settings.model_dir
        xp = os.path.join(d, "xgb_1x2.pkl")
        lp = os.path.join(d, "lgbm_1x2.pkl")
        cp = os.path.join(d, "catboost_1x2.pkl")
        cal_p = os.path.join(d, "calibrators_1x2.pkl")

        if os.path.exists(xp) and os.path.exists(lp):
            self.xgb_model = joblib.load(xp)
            self.lgbm_model = joblib.load(lp)
            if os.path.exists(cp):
                self.catboost_model = joblib.load(cp)
            if os.path.exists(cal_p):
                self.calibrators = joblib.load(cal_p)
            self.is_fitted = True
            logger.info("1X2 models loaded")
        else:
            logger.warning(f"Model files not found in {d}")
