# Libraries needed....

# Additional installs
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "catboost", "-q"])
subprocess.check_call([sys.executable, "-m", "pip", "install", "pyod", "-q"])

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Date for CVs
from datetime import datetime

# To showhow long the model ran
import time

# Models:
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from xgboost import XGBClassifier
from catboost import CatBoostClassifier, Pool
from sklearn.ensemble import ExtraTreesClassifier
import lightgbm as lgb
from sklearn.tree import DecisionTreeClassifier

# Undersampling Methods:
from imblearn.under_sampling import RandomUnderSampler
from CBU_Cleanse import CLEANSE

# Feature Selection Methods:
from sklearn.feature_selection import SelectKBest

# Standerdizing
from sklearn.preprocessing import StandardScaler

# Pipeline
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.model_selection import GroupShuffleSplit # Using this data is split into train and test while being group concious

# Evaluation Metrics
from sklearn.metrics import f1_score, precision_score, recall_score, ConfusionMatrixDisplay, average_precision_score, roc_auc_score, confusion_matrix

# Shapley
import shap

# Warning handling
import warnings
warnings.filterwarnings("ignore")

# Storing Metrics
import json

# Install pyod if not available
try:
    from pyod.models.inne import INNE as INNE_Model
    from sklearn.feature_selection import SelectKBest, mutual_info_classif
    INNE_AVAILABLE = True
except Exception:
    INNE_AVAILABLE = False
    print("INNE not installed")

#-----------------------------------------------------------------------------------------------------------------------

BIN_PERCENTILES = [50, 90, 95]
BIN_LABELS = ['Low', 'Medium', 'High', 'Critical']

#-----------------------------------------------------------------------------------------------------------------------

MODEL_REGISTRY = {
    "logistic_regression": {"estimator": LogisticRegression(max_iter=1000, random_state=42)},
    "xgboost": {"estimator": XGBClassifier(random_state=42, eval_metric="logloss", verbosity=0)},
    "svm": {"estimator": SVC(probability=True, random_state=42)}
}

#-----------------------------------------------------------------------------------------------------------------------

UNDERSAMPLE_REGISTRY = {
    # RandomUnderSampler will act as the base line
    "RandomUnderSampler": RandomUnderSampler(sampling_strategy=0.09, random_state=42),
    # CLEANSE, a smart cluster-based undersampling method, its the slowest undersampling method yet.
    "CLEANSE": CLEANSE(distance='auto', inhomo=True, k_neighbors=6, k_min=20, k_max=22, random_state=42)
}

#-----------------------------------------------------------------------------------------------------------------------

def catboost_prediction_change_scorer(X, y):
    # Initialize and fit a temporary model
    model = CatBoostClassifier(iterations=100, random_seed=42, verbose=False)
    model.fit(X, y)

    # Extract PredictionValuesChange importance
    scores = model.get_feature_importance(type='PredictionValuesChange')

    # SelectKBest expects (scores, p_values); return dummy p-values
    return scores, [None] * len(scores)

#-----------------------------------------------------------------------------------------------------------------------

def xgb_gain_scorer(X, y):
    # Initialize and fit a temporary model
    model = XGBClassifier(objective='binary:logistic', importance_type='gain', random_state=42)
    model.fit(X, y)

    # Extract gain importance
    scores = model.feature_importances_

    # SelectKBest expects (scores, p_values); return dummy p-values
    return scores, [None] * len(scores)

#-----------------------------------------------------------------------------------------------------------------------

def lgbm_split_scorer(X, y):
    # Initialize and fit a temporary model
    model = lgb.LGBMClassifier(random_state=42, verbosity=-1)
    model.fit(X, y)

    # Extract gain importance
    scores = model.feature_importances_

    # SelectKBest expects (scores, p_values); return dummy p-values
    return scores, [None] * len(scores)

#-----------------------------------------------------------------------------------------------------------------------

def decision_tree_gini_scorer(X, y):
    # Initialize and fit a temporary model
    model = DecisionTreeClassifier(random_state=42)
    model.fit(X, y)

    # Extract gain importance
    scores = model.feature_importances_

    # SelectKBest expects (scores, p_values); return dummy p-values
    return scores, [None] * len(scores)

#-----------------------------------------------------------------------------------------------------------------------

FEATURE_SELECTION_REGISTRY = {
    "k_best_catboost": SelectKBest(score_func=catboost_prediction_change_scorer),
    "k_best_xgb": SelectKBest(score_func=xgb_gain_scorer),
    "k_best_lgbm": SelectKBest(score_func=lgbm_split_scorer),
    "k_best_decision_tree": SelectKBest(score_func=decision_tree_gini_scorer)
}

#-----------------------------------------------------------------------------------------------------------------------

def add_inne_features(
    df: pd.DataFrame,
    transaction_data_path: str,
    group_col: str = "npi",
    year_col: str = "year",
    txn_provider_col: str = "covered_recipient_npi",
    txn_year_col: str = "program_year",
    txn_target_col: str = "target",
    txn_id_cols: list[str] | None = None,
    n_estimators: int = 100,
    max_samples: int = 8,
    contamination: float = 0.0005,
    random_state: int = 42,
    top_k_features: int = 15,
    null_fill: float = -1,
    verbose: int = 1,
) -> pd.DataFrame:
    """
    Runs INNE on transaction-level data, rolls up scores to provider-year,
    and left-joins 3 anomaly features onto the unified dataset.

    Returns the unified df with: inne_score_mean, inne_n_above_p{X}, inne_pct_above_p{X}
    where X is the last value in BIN_PERCENTILES (dynamic).
    """

    if not INNE_AVAILABLE:
        raise ImportError("pyod is required. Install with: pip install pyod")

    if txn_id_cols is None:
        txn_id_cols = [txn_provider_col, "record_id", txn_year_col]


    ##########################################
    # LOAD AND PREP TRANSACTION DATA
    ##########################################

    if verbose >= 1:
        print(f"INNE: Loading {transaction_data_path}")

    txn_df = pd.read_csv(transaction_data_path).fillna(null_fill)

    # Drop ID and target columns, keep only numeric features
    drop_cols = [c for c in txn_id_cols + [txn_target_col] if c in txn_df.columns]
    X = txn_df.drop(columns=drop_cols).select_dtypes(include=[np.number]).fillna(null_fill)
    y = txn_df[txn_target_col].astype(int).values

    # Feature selection via mutual information
    k = min(top_k_features, X.shape[1])
    selector = SelectKBest(score_func=mutual_info_classif, k=k)
    selector.fit(X, y)
    X = X.loc[:, selector.get_support()].values

    if verbose >= 1:
        print(f"INNE: {txn_df.shape[0]} transactions, {k} features selected")


    ##########################################
    # SCALE AND FIT INNE
    ##########################################

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = INNE_Model(
        n_estimators=n_estimators,
        max_samples=max_samples,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(X_scaled)

    if verbose >= 1:
        print(f"INNE: Fitted with n_estimators={n_estimators}, max_samples={max_samples}, contamination={contamination}")


    ##########################################
    # SCORE AND COMPUTE TOP-BIN THRESHOLD
    ##########################################

    _top_pct = BIN_PERCENTILES[-1]
    all_scores = model.decision_function(X_scaled)
    TOP_CUTOFF = np.percentile(all_scores, _top_pct)

    if verbose >= 1:
        print(f"INNE: Score range=[{all_scores.min():.4f}, {all_scores.max():.4f}], P{_top_pct} cutoff={TOP_CUTOFF:.4f}")


    ##########################################
    # ROLL UP TO PROVIDER-YEAR
    ##########################################

    rollup = txn_df[[txn_provider_col, txn_year_col]].copy()
    rollup["inne_score"] = all_scores

    _n_col   = f"inne_n_above_p{_top_pct}"
    _pct_col = f"inne_pct_above_p{_top_pct}"

    agg = rollup.groupby([txn_provider_col, txn_year_col]).agg(
        inne_score_mean = ("inne_score", "mean"),
        **{_n_col:   ("inne_score", lambda s: (s >= TOP_CUTOFF).sum())},
        **{_pct_col:  ("inne_score", lambda s: (s >= TOP_CUTOFF).mean())},
    ).reset_index()

    if verbose >= 1:
        flagged = (agg[_n_col] > 0).sum()
        print(f"INNE: Rolled up to {agg.shape[0]} provider-years, {flagged} with any above P{_top_pct}")


    ##########################################
    # LEFT JOIN ONTO UNIFIED DATASET
    ##########################################
    agg = agg.rename(columns={txn_provider_col: group_col, txn_year_col: year_col}) # rename the columns so that the npi and the years are the same names
    df_out = df.merge(agg, on=[group_col, year_col], how="left")

    # Drop duplicate join keys from transaction side
    for col in [txn_provider_col, txn_year_col]:
        if col != group_col and col != year_col and col in df_out.columns:
            df_out = df_out.drop(columns=col)

    # Fill unmatched providers with 0
    inne_cols = ["inne_score_mean", _n_col, _pct_col]
    df_out[inne_cols] = df_out[inne_cols].fillna(0)

    if verbose >= 1:
        matched = df_out["inne_score_mean"].ne(0).sum()
        print(f"INNE: Joined -> {df_out.shape}, {matched}/{len(df_out)} matched ({matched/len(df_out)*100:.1f}%)")

    return df_out

#-----------------------------------------------------------------------------------------------------------------------

def extract_features(df: pd.DataFrame,target_col: str,exclude_cols: list[str]) -> pd.DataFrame:
    cols_to_drop = [target_col] + [c for c in exclude_cols if c in df.columns]
    temp = df.drop(columns=cols_to_drop).select_dtypes(include=[np.number])
    return temp

#-----------------------------------------------------------------------------------------------------------------------

class MLPipeline:

    # Default parameters
    def __init__(self, model_name: str = "logistic_regression", target_col: str = "target", test_size: float = 0.4,
                 cv: int = 5, scoring: str = "average_precision", random_state: int = 42, verbose: int = 1, ):
        if model_name not in MODEL_REGISTRY:
            raise ValueError(f"Unknown model '{model_name}'.\nAvailable: {list(MODEL_REGISTRY.keys())}")

        # Initializes with parameters provided by user (Uses default from _init_ if some are missing)
        self.model_name = model_name
        self.target_col = target_col
        self.test_size = test_size
        self.cv = cv
        self.scoring = scoring
        self.random_state = random_state
        self.verbose = verbose

        # Empty right now but assigned respective values after train()
        self.best_estimator_ = None
        self.best_params_ = None
        self.best_cv_score_ = None
        self.results_ = None
        self.training_time_ = None
        self.cv_results_ = None
        self.X_train_ = None
        self.X_test_ = None
        self.y_train_ = None
        self.y_test_ = None
        self.group_col_ = None
        self.group_ids_test_ = None

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    # Helper functions (Trying something new)

    # Returns a list of all available models
    @staticmethod
    def list_models():
        return list(MODEL_REGISTRY.keys())

    # Returns a list of all available undersampling methods
    @staticmethod
    def list_undersample_methods():
        return list(UNDERSAMPLE_REGISTRY.keys())

    # Returns a list of all available feature selection methods
    @staticmethod
    def list_feature_selection_methods():
        return list(FEATURE_SELECTION_REGISTRY.keys())

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def _print_summary(self):

        # Quick summary of the model
        print("\n" + "-" * 150)
        print("\n")
        # Finding the standard deviation of validation scores across cross-validation folds
        best_idx = self.cv_results_["rank_test_score"].argmin()
        best_std = self.cv_results_["std_test_score"][best_idx]

        # Across each fold, storing the score of the best paramaeter combination
        fold_scores = np.array([self.cv_results_[f"split{i}_test_score"][best_idx] for i in range(self.cv)])

        # Across each fold, storing the fit times of the best paramaeter combination  (Not really needed, but lets see for now)
        fold_fit_times = np.array([self.cv_results_[f"split{i}_fit_time"][best_idx] for i in
                                   range(self.cv)]) if f"split0_fit_time" in self.cv_results_ else None

        cv = best_std / self.best_cv_score_ if self.best_cv_score_ != 0 else float("nan")

        print(f"Model: {self.model_name}")
        print(f"CV folds: {self.cv}  |  Scoring: {self.scoring}")
        print(f"Best CV score: {self.best_cv_score_:.4f} ± {best_std:.4f} (std across folds)")
        print(f"Score range: min = {fold_scores.min():.4f}  max = {fold_scores.max():.4f}  cv = {cv:.4f} (std/mean)")
        print(f"Training time: {round(self.training_time_, 1)} Seconds")
        print(f"Best params: {self.best_params_}")

        # Prints each folds details
        # Titles
        print("\nPer-fold breakdown:")
        print(f"  {'Fold':<8} {'Score':>10}", end="")
        if fold_fit_times is not None:
            print(f"  {'Fit time (s)':>12}", end="")
        print()

        # Actual Score
        for i, score in enumerate(fold_scores):
            line = f"  {i + 1:<8} {score:>10.4f}"
            if fold_fit_times is not None:
                line += f"  {fold_fit_times[i]:>12.2f}"
            print(line)

        print("\n")
        print("-" * 150)
        print("\n")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def _plot_precision_at_k(self, precision_at_k, K_VALUES, output_dir):
        # Plots the precision@k values
        # First to check if there any values and not just zero
        valid = {k: v for k, v in precision_at_k.items() if v is not None and v > 0}

        if not valid:
            if self.verbose >= 1:
                print("\nSkipping Precision@K plot since there no valid values.")
                print("\n")
                print("-" * 150)
                print("\n")
            return

        labels = list(valid.keys())
        values = list(valid.values())

        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(labels, values, color="steelblue", edgecolor="none", width=0.5)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{val:.4f}",
                ha="center", va="bottom", fontsize=9)

        ax.set_ylim(0, max(values) * 1.2)
        ax.set_xlabel("K")
        ax.set_ylabel("Precision")
        ax.set_title(f"{self.model_name} - Precision@K", fontweight="bold")
        plt.tight_layout()

        # Save the plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{output_dir}/{self.model_name}_precision_at_k_{timestamp}.png"
        plt.savefig(path, dpi=360)
        plt.close()

        if self.verbose >= 1:
            print(f"\nPrecision@K plot saved in path:{path}")
            print("\n")
            print("-" * 150)
            print("\n")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def _compute_metrics(self, y_true, y_pred, y_proba, output_dir) -> dict:
        # Calculates the metrics and returns it as a simple dictionary
        K_VALUES = [10, 20, 50, 100]  # Finding Precision@k
        sorted_indices = np.argsort(y_proba)[::-1]  # Sorts them in decending order....
        sorted_labels = np.array(y_true)[sorted_indices]

        precision_at_k = {}

        for k in K_VALUES:
            if k > len(sorted_labels):
                # if k exceeds the test set size, skip rather than error, alot more safer
                precision_at_k[f"precision@{k}"] = None
            else:
                top_k_labels = sorted_labels[:k]
                precision_at_k[f"precision@{k}"] = round(top_k_labels.sum() / k, 5)

        metrics = {
            "auc_roc": round(roc_auc_score(y_true, y_proba), 4),
            "auprc": round(average_precision_score(y_true, y_proba), 4),
            "f1_macro": round(f1_score(y_true, y_pred, average="macro"), 4),
            "precision_macro": round(precision_score(y_true, y_pred, average="macro", zero_division=0), 4),
            "recall_macro": round(recall_score(y_true, y_pred, average="macro", zero_division=0), 4),
            "best_cv_score": round(self.best_cv_score_, 4),
            "training_time": round(self.training_time_, 1),
            **precision_at_k,
            "best_params": self.best_params_,
        }

        self._plot_precision_at_k(precision_at_k, K_VALUES, output_dir)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{output_dir}/{self.model_name}_metrics_{timestamp}.txt"

        # Loading the metrics on to a txt file
        exDict = {'metrics': metrics}
        with open(path, 'w') as file:
            file.write(json.dumps(exDict))

        if self.verbose >= 1:
            print(f"\nMetrics saved in path:{path}")
            print("\n")
            print("-" * 150)
            print("\n")

        return metrics

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def _plot_score_distribution(self, train_scores, test_scores, output_dir):

        # Finds the cutoff
        cutoffs = np.percentile(test_scores, BIN_PERCENTILES)
        fig, ax = plt.subplots(figsize=(10, 5))

        ax.hist(train_scores, bins=80, alpha=0.55, label="Train", color="steelblue", edgecolor="none")
        ax.hist(test_scores, bins=80, alpha=0.55, label="Test", color="coral", edgecolor="none")

        for cutoff, label in zip(cutoffs, BIN_LABELS[1:]):
            ax.axvline(cutoff, linestyle="--", linewidth=1.5, label=f"{label} cutoff ({cutoff:.2f})")

        ax.set_xlabel("Predicted Probability (higher = more likely positive)")
        ax.set_ylabel("Frequency")
        ax.set_title(f"{self.model_name} — Score Distribution with Risk Tier Cutoffs", fontweight="bold")
        ax.legend(fontsize=8)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{output_dir}/{self.model_name}_score_dist_{timestamp}.png"
        plt.savefig(path, dpi=360)
        plt.close()

        if self.verbose >= 1:
            print(f"\nScore distribution plot saved in path: {path}")
            print("\n")
            print("-" * 150)
            print("\n")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def _plot_confusion_matrix(self, y_true, y_pred, output_dir):

        # Creates a confusion matrix and saves it
        cm = confusion_matrix(y_true, y_pred)
        plt.figure(figsize=(5, 4))
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Normal', 'Fraud'],
                    yticklabels=['Normal', 'Fraud'])
        plt.title(f'Confusion Matrix - {self.model_name}')
        plt.ylabel('Actual')
        plt.xlabel('Predicted')
        plt.tight_layout()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{output_dir}/{self.model_name}_confusion_matrix_{timestamp}.png"
        plt.savefig(path, dpi=360)
        plt.close()

        if self.verbose >= 1:
            print(f"\nConfusion matrix saved in path: {path}")
            print("\n")
            print("-" * 150)
            print("\n")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def _save_scores_csv(self, X_test, y_test, test_proba, group_ids, group_col, output_dir):

        # Give each test entry a label.......
        cutoffs = np.percentile(test_proba, BIN_PERCENTILES)
        unique_cutoffs = sorted(set(cutoffs))

        bins = [-np.inf] + unique_cutoffs + [np.inf]
        labels = BIN_LABELS[:len(bins) - 1]

        tiers = pd.cut(test_proba, bins=bins, labels=labels, duplicates="drop")

        # Need to update this to include NPI as well or anthing other identifyer
        # Updated heheheheh
        scores_df = pd.DataFrame({
            group_col: group_ids,
            "true_label": y_test,
            "predicted_score": test_proba,
            "risk_tier": tiers
        }, index=X_test.index)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{output_dir}/{self.model_name}_{timestamp}.csv"
        scores_df.to_csv(path, index=True)

        if self.verbose >= 1:
            print(f"\nScores CSV saved in path: {path}")
            print("\n")
            print("-" * 150)
            print("\n")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def _explain(self, X_train, X_test, output_dir):

        kernel_sample_size = 100  # Default valuethats only ever used when SVM model is used.

        # The function produces SHAP explanation plots
        raw_model = self.best_estimator_.named_steps["model"]
        scaler = self.best_estimator_.named_steps["scaler"]
        selector = self.best_estimator_.named_steps["selector"]

        X_train_selected = selector.transform(X_train)
        X_test_selected = selector.transform(X_test)

        selected_features = X_train.columns[selector.get_support()].tolist()

        # Data needs to be scaled here......
        X_train_scaled = pd.DataFrame(scaler.transform(X_train_selected), columns=selected_features)
        X_test_scaled = pd.DataFrame(scaler.transform(X_test_selected), columns=selected_features)

        # SVM uses a different explainer, so we have to use else-if condition

        if self.model_name in ("xgboost", "logistic_regression"):
            explainer = shap.Explainer(raw_model, X_train_scaled)
            shap_values = explainer(X_test_scaled)

        elif self.model_name == "svm":
            background = shap.sample(X_train_scaled, kernel_sample_size)
            explainer = shap.KernelExplainer(lambda x: raw_model.predict_proba(x)[:, 1], background)
            X_test_scaled = X_test_scaled.sample(n=min(100, len(X_test_scaled)),
                                                 random_state=42)  # We need to set a very small sample subset, otherwise it will take too long.
            shap_values = explainer(X_test_scaled)

        else:
            raise ValueError(f"SHAP explanation not configured for model '{self.model_name}'.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Bar plot (feature importance)
        plt.figure()
        shap.summary_plot(shap_values, X_test_scaled, plot_type="bar", show=False, feature_names=X_test.columns)
        plt.title(f"{self.model_name} — SHAP Feature Importance")
        plt.tight_layout()
        path = f"{output_dir}/{self.model_name}_shap_importance_{timestamp}.png"
        plt.savefig(path, dpi=360, bbox_inches="tight")
        plt.close()
        if self.verbose >= 1:
            print(f"SHAP importance plot saved in path:{path}")
            print("\n")
            print("-" * 150)
            print("\n")

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def train(self, df: pd.DataFrame, param_grid: dict, group_col: str, exclude_cols: list[str] | None = None,
              undersample_method: str | None = None, feature_selection_method: str | None = None,
              output_dir: str = "."):

        # Added a "None" option for undersamping method and excluded columns.
        # This way you can test performance of the model on the data with/without undersampling while also not making it mandetory to pass a excluded column list
        exclude_cols = list(exclude_cols or [])

        # Sometimes the identifier might not be exclude. This adds it in the exclusion list just in case to prevent data leakage.
        if group_col not in exclude_cols:
            exclude_cols.append(group_col)

        X = extract_features(df, self.target_col,
                             exclude_cols)  # Uses the extract_feature function to remove the necessary features
        y = df[self.target_col]

        # Train and test split
        # Test size default has beeb changed to 0.4 from 0.2
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=self.test_size,
                                                            random_state=self.random_state, stratify=y)

        # Storing the groups in train for stratifiedKfold
        groups_train = df.loc[X_train.index, group_col].to_numpy()

        # Undersampling portion of the code
        if undersample_method is not None:
            if undersample_method not in UNDERSAMPLE_REGISTRY:
                raise ValueError(
                    f"Unknown undersample method '{undersample_method}'.\nAvailable: {list(UNDERSAMPLE_REGISTRY.keys())}")
            sampler = UNDERSAMPLE_REGISTRY[undersample_method]
            X_train, y_train = sampler.fit_resample(X_train, y_train)

            # need to redo the group_train after undersampling of train data......
            # updated this hehehehehe
            groups_train = groups_train[sampler.sample_indices_]

            if self.verbose >= 1:
                unique, counts = np.unique(y_train, return_counts=True)
                print(f"\nUndersampling ({undersample_method}) applied.")
                print(f"Class distribution after undersampling: {dict(zip(unique, counts))}")

        # Feature selection portion of the code
        if feature_selection_method is not None:
            if feature_selection_method not in FEATURE_SELECTION_REGISTRY:
                raise ValueError(
                    f"Unknown feature selection method '{feature_selection_method}'.\nAvailable: {list(UNDERSAMPLE_REGISTRY.keys())}")
            if self.verbose >= 1:
                print(f"\nFeature Selection ({feature_selection_method}) selected.")

        pipeline = Pipeline([("selector", FEATURE_SELECTION_REGISTRY[feature_selection_method]),
                             ("scaler", StandardScaler()), ("model", MODEL_REGISTRY[self.model_name]["estimator"])])

        # GridSearchCV with StratifiedGroupKFold
        cv_splitter = StratifiedGroupKFold(n_splits=self.cv)

        grid_search = GridSearchCV(
            pipeline,
            param_grid=param_grid,
            cv=cv_splitter,
            scoring=self.scoring,
            n_jobs=-1,
            verbose=self.verbose,
        )

        startT = time.time()
        grid_search.fit(X_train, y_train, groups=groups_train)
        self.training_time_ = time.time() - startT  # How long the training took

        self.best_estimator_ = grid_search.best_estimator_
        self.best_params_ = grid_search.best_params_
        self.best_cv_score_ = grid_search.best_score_
        self.cv_results_ = grid_search.cv_results_
        self.X_train_ = X_train
        self.X_test_ = X_test
        self.y_train_ = y_train
        self.y_test_ = y_test
        self.group_col_ = group_col
        self.group_ids_test_ = df.loc[X_test.index, group_col]

        if self.verbose >= 1:
            self._print_summary()  # Quick summary of the model

    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    def test(self, output_dir: str = "."):

        # Ensuring train() was run before test()
        if self.best_estimator_ is None:
            raise RuntimeError("No model was train. Please run train() before test().")

        # Evaluating performance of the model using test data
        test_proba = self.best_estimator_.predict_proba(self.X_test_)[:, 1]
        train_proba = self.best_estimator_.predict_proba(self.X_train_)[:, 1]
        y_pred = self.best_estimator_.predict(self.X_test_)

        self.results_ = self._compute_metrics(self.y_test_, y_pred, test_proba,
                                              output_dir)  # gets and stores the metrics

        if self.verbose >= 1:
            print("Test-set metrics:")
            for k, v in self.results_.items():
                print(f" {k:<20} {v}")
            print("\n")
            print("-" * 150)
            print("\n")

        # Visuals (Will change; more or less visuals)
        self._plot_score_distribution(train_proba, test_proba, output_dir)  # Score distribtution plot
        self._plot_confusion_matrix(self.y_test_, y_pred, output_dir)  # Confusion matrix plot

        # Saving scores
        self._save_scores_csv(self.X_test_, self.y_test_, test_proba, self.group_ids_test_, self.group_col_, output_dir)

        self._explain(self.X_train_, self.X_test_, output_dir)  # Feature importance with Shapley

#-----------------------------------------------------------------------------------------------------------------------

if __name__ == "__main__":

    print('Hello there!\nKindly refer the "How will this be used" portion of the notebook to run the pipeline. That being said, this cell can be used for testing purposes.')
    print('\nTesting to be done below the line.\n')
    print('-'*150)