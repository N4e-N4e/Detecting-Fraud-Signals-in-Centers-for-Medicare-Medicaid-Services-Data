# Libraries needed.....

import pandas as pd
import numpy as np

# Normalize that data
from sklearn.preprocessing import MinMaxScaler

# K-means
from sklearn.cluster import KMeans

# Silhouette Coefficient
from sklearn.metrics import silhouette_score

# Nearest Neighbour
from sklearn.neighbors import NearestNeighbors


def optimal_dist_param(distances, n_ranges=5, percentage=0.7):
    # array of distances from each sample to its centroid
    # n_ranges    : number of distance buckets to create (default 5) as mentioned in the paper
    # percentage  : target fraction of samples to remove (default 0.7) as mentioned in the paper
    if len(distances) == 0:
        return 0.0

    max_dist = distances.max()
    if max_dist == 0:
        return 0.0

    # Normalize distances to [0, 1]
    norm_distances = distances / max_dist

    # Split [0,1] into n_ranges equal buckets and count samples per bucket
    bins = np.linspace(0, 1, n_ranges + 1)
    counts, _ = np.histogram(norm_distances, bins=bins)
    total = len(distances)

    # Find the bucket whose cumulative proportion sits in [percentage, percentage+0.1]
    cumulative = 0.0
    for i, count in enumerate(counts):
        cumulative += count / total
        if percentage <= cumulative <= percentage + 0.1:
            return bins[i + 1]  # upper edge of this bucket is the threshold


    return percentage


def find_optimal_k(X, k_min, k_max, random_state=42):
    # X : dataset
    # k_min : minimum clusters to try (default 20)
    # k_max : maximum clusters to try (default 30)

    best_k = k_min
    best_score = -1.0

    # Cap k_max so we never request more clusters than samples
    k_max = min(k_max, len(X) - 1)

    for k in range(k_min, k_max + 1):
        kmeans = KMeans(n_clusters=k, random_state=random_state, n_init=10)
        labels = kmeans.fit_predict(X)

        # Silhouette requires a minimum 2 distinct cluster labels
        if len(np.unique(labels)) < 2:
            continue

        score = silhouette_score(X, labels)
        if score > best_score:
            best_score = score
            best_k = k

    #print(f"Best k={best_k} (silhouette={best_score:.4f})")
    return best_k


class CLEANSE:

    def __init__(self, distance='auto', inhomo=True, k_neighbors=6, k_min=20, k_max=30, majority_label=0, minority_label=1, random_state=42):
        self.distance = distance
        self.inhomo = inhomo
        self.k_neighbors = k_neighbors
        self.k_min = k_min
        self.k_max = k_max
        self.majority_label = majority_label
        self.minority_label = minority_label
        self.random_state = random_state

        self.scaler_ = None
        self.kmeans_ = None
        self.n_removed_ = 0

    def _normalize(self, X):
        # Normalizing the data
        self.scaler_ = MinMaxScaler()
        return self.scaler_.fit_transform(X)

    def _denormalize(self, X_scaled):
        # Reversing the normalization
        return self.scaler_.inverse_transform(X_scaled)

    # Process a Homogeneous Majority Cluster
    # Removes samples closest to the centroid.
    def _process_homogeneous_majority(self, cluster_indices, X_scaled, centroid):

        # Logic: compute each sample's distance to the centroid,
        # then remove those within [distance threshold * max_dist].
        # Closest-to-center = most redundant = safe to remove.

        X_cluster = X_scaled[cluster_indices]
        distances = np.linalg.norm(X_cluster - centroid, axis=1)

        # Determine distance threshold
        if self.distance == 'auto':
            dist_param = optimal_dist_param(distances)
        else:
            dist_param = self.distance  # can be provided by user

        max_dist = distances.max()
        threshold = dist_param * max_dist

        # Flag samples within threshold distance from centroid
        to_remove = set()
        for i, (idx, dist) in enumerate(zip(cluster_indices, distances)):
            if dist <= threshold:
                to_remove.add(idx)

        return to_remove

    # Process an Inhomogeneous (Mixed) Cluster
    # Removes majority samples that are nearest neighbors of minority samples.
    # These boundary-hugging legitimate claims blur the fraud decision boundary.
    def _process_inhomogeneous(self, cluster_indices, X_scaled, y):
        # Flag majority samples that are k-nearest neighbors of minority samples.

        # Logic: for each fraud sample in the cluster, find its k nearest. By default it is set up as 6.
        # legitimate-claim neighbors. Those are the ambiguous boundary points that hurt classifier performance, remove them.

        to_remove = set()

        cluster_mask = np.array(cluster_indices)
        y_cluster = y[cluster_mask]

        minority_mask = y_cluster == self.minority_label
        majority_mask = y_cluster == self.majority_label

        minority_indices = cluster_mask[minority_mask]
        majority_indices = cluster_mask[majority_mask]

        # Ensuring that is atleast 1 entry of each class
        if len(minority_indices) == 0 or len(majority_indices) == 0:
            return to_remove

        X_majority = X_scaled[majority_indices]
        X_minority = X_scaled[minority_indices]

        # Fit KNN on majority samples only
        k = min(self.k_neighbors, len(majority_indices))
        nbrs = NearestNeighbors(n_neighbors=k, metric='euclidean')
        nbrs.fit(X_majority)

        # For each fraud sample, find its k nearest legitimate neighbors
        _, neighbor_positions = nbrs.kneighbors(X_minority)

        # Flag those majority neighbors for removal
        # Note: all flagging happens before any removal so order doesn't matter
        for positions in neighbor_positions:
            for pos in positions:
                to_remove.add(majority_indices[pos])

        return to_remove

    # Main fit_resample Entry Point
    def fit_resample(self, X, y):
        # Main Function to run

        # Ensures provided data are DataFrames
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values

        X = np.array(X, dtype=float)
        y = np.array(y)


        # Normalize the data
        X_scaled = self._normalize(X)

        # Find optimal K vlaue
        best_k = find_optimal_k(
            X_scaled,
            k_min=self.k_min,
            k_max=self.k_max,
            random_state=self.random_state
        )

        # K-means clustering + per-cluster processing
        self.kmeans_ = KMeans(n_clusters=best_k, random_state=self.random_state, n_init=10)
        cluster_labels = self.kmeans_.fit_predict(X_scaled)
        centroids = self.kmeans_.cluster_centers_

        all_flagged = set()

        for cluster_id in range(best_k):
            cluster_indices = np.where(cluster_labels == cluster_id)[0]
            y_in_cluster = y[cluster_indices]

            has_majority = np.any(y_in_cluster == self.majority_label)
            has_minority = np.any(y_in_cluster == self.minority_label)

            # Classify the cluster type
            if not has_majority and has_minority:
                # Pure fraud cluster, keep
                flagged = set()

            elif has_majority and not has_minority:
                # Pure legitimate cluster, remove
                flagged = self._process_homogeneous_majority(
                    cluster_indices, X_scaled, centroids[cluster_id]
                )

            else:
                # Mixed cluster, flag k points close to the points that are fraud
                if self.inhomo:
                    flagged = self._process_inhomogeneous(
                        cluster_indices, X_scaled, y
                    )
                else:
                    flagged = set()

            all_flagged.update(flagged)

        # Remove flagged samples
        self.n_removed_ = len(all_flagged)
        keep_mask = np.ones(len(y), dtype=bool)
        keep_mask[list(all_flagged)] = False

        X_kept = X_scaled[keep_mask]
        y_kept = y[keep_mask]

        # Reverse normalization
        X_resampled = self._denormalize(X_kept)
        y_resampled = y_kept

        # Store the indices for the groupkfold
        self.sample_indices_ = np.where(keep_mask)[0]

        return X_resampled, y_resampled

if __name__ == "__main__":
    print('Hello there!\nKindly refer the "How will this be used" portion of the notebook to run the pipeline. That being said, this cell can be used for testing purposes.')
    print('\nTesting to be done below the line.\n')
    print('-'*150)
    print('-' * 150)
