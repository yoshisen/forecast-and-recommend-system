"""
Recommendation Models - 推薦システム
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)


class CollaborativeFilter:
    """協同フィルタリング（簡易版 - User-Based）"""
    
    def __init__(self, min_interactions: int = 3):
        self.min_interactions = min_interactions
        self.user_item_matrix = None
        self.similarity_matrix = None
        self.user_ids = None
        self.item_ids = None
    
    def fit(self, interaction_df: pd.DataFrame):
        """学習"""
        logger.info("Training collaborative filtering model")
        
        # User-Item マトリックスを作成
        if 'customer_id' not in interaction_df.columns or 'product_id' not in interaction_df.columns:
            raise ValueError("customer_id と product_id が必要です")
        
        # ピボットテーブル作成
        score_col = 'purchase_count' if 'purchase_count' in interaction_df.columns else 'quantity'
        
        self.user_item_matrix = interaction_df.pivot_table(
            index='customer_id',
            columns='product_id',
            values=score_col,
            fill_value=0
        )
        
        self.user_ids = self.user_item_matrix.index.tolist()
        self.item_ids = self.user_item_matrix.columns.tolist()
        
        # ユーザー間類似度を計算
        self.similarity_matrix = cosine_similarity(self.user_item_matrix)
        
        logger.info(f"Matrix shape: {self.user_item_matrix.shape}, Users: {len(self.user_ids)}, Items: {len(self.item_ids)}")
        
        return self
    
    def recommend(self, user_id: str, top_k: int = 10, exclude_purchased: bool = True) -> List[Tuple[str, float]]:
        """推薦生成"""
        if self.user_item_matrix is None:
            raise ValueError("モデルが学習されていません")
        
        if user_id not in self.user_ids:
            # 新規ユーザー - 人気商品を返す
            return self._get_popular_items(top_k)
        
        user_idx = self.user_ids.index(user_id)
        
        # ユーザーの類似ユーザーを取得
        similarities = self.similarity_matrix[user_idx]
        
        # 類似度の高いユーザーを選択（自分自身を除く）
        similar_users_idx = np.argsort(similarities)[::-1][1:min(21, len(similarities))]
        
        # 類似ユーザーの評価を集計
        similar_users_ratings = self.user_item_matrix.iloc[similar_users_idx]
        weighted_ratings = similar_users_ratings.T.dot(similarities[similar_users_idx])
        
        # ユーザーが既に購入した商品を除外
        if exclude_purchased:
            user_ratings = self.user_item_matrix.iloc[user_idx]
            purchased_items = user_ratings[user_ratings > 0].index.tolist()
            weighted_ratings = weighted_ratings.drop(purchased_items, errors='ignore')
        
        # Top-K を取得
        top_items = weighted_ratings.nlargest(top_k)
        
        return [(item, score) for item, score in top_items.items()]
    
    def _get_popular_items(self, top_k: int) -> List[Tuple[str, float]]:
        """人気商品を取得（コールドスタート用）"""
        item_popularity = self.user_item_matrix.sum(axis=0).nlargest(top_k)
        return [(item, score) for item, score in item_popularity.items()]


class ContentBasedRecommender:
    """コンテンツベース推薦"""
    
    def __init__(self):
        self.product_features = None
        self.similarity_matrix = None
        self.product_ids = None
    
    def fit(self, product_df: pd.DataFrame):
        """学習"""
        logger.info("Training content-based recommender")
        
        self.product_features = product_df.copy()
        
        # カテゴリ特徴をエンコード
        category_cols = [col for col in product_df.columns if 'category' in col.lower()]
        
        if category_cols:
            # One-hot エンコーディング
            encoded = pd.get_dummies(product_df[category_cols], prefix=category_cols)
            
            # 価格特徴（正規化）
            if 'retail_price_jpy' in product_df.columns:
                price_normalized = (product_df['retail_price_jpy'] - product_df['retail_price_jpy'].mean()) / product_df['retail_price_jpy'].std()
                encoded['price_normalized'] = price_normalized
            
            # 類似度計算
            self.similarity_matrix = cosine_similarity(encoded.fillna(0))
            self.product_ids = product_df['product_id'].tolist() if 'product_id' in product_df.columns else product_df.index.tolist()
            
            logger.info(f"Computed similarity for {len(self.product_ids)} products")
        
        return self
    
    def recommend(self, product_id: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """類似商品を推薦"""
        if self.similarity_matrix is None:
            raise ValueError("モデルが学習されていません")
        
        if product_id not in self.product_ids:
            return []
        
        product_idx = self.product_ids.index(product_id)
        similarities = self.similarity_matrix[product_idx]
        
        # Top-K 類似商品（自分自身を除く）
        similar_idx = np.argsort(similarities)[::-1][1:top_k+1]
        
        recommendations = []
        for idx in similar_idx:
            recommendations.append((self.product_ids[idx], similarities[idx]))
        
        return recommendations


class HybridRecommender:
    """ハイブリッド推薦システム"""
    
    def __init__(self, 
                 cf_weight: float = 0.6, 
                 content_weight: float = 0.4,
                 min_interactions: int = 3):
        self.cf_weight = cf_weight
        self.content_weight = content_weight
        self.cf_model = CollaborativeFilter(min_interactions)
        self.content_model = ContentBasedRecommender()
        self.popular_items = []
        self.interaction_df = None
        self.product_df = None

    @staticmethod
    def _normalize_scores(sorted_recs: List[Tuple[str, float]]) -> Dict[str, float]:
        if not sorted_recs:
            return {}

        scores = np.array([float(score) for _, score in sorted_recs], dtype=float)
        max_score = float(np.max(scores))

        if not np.isfinite(max_score) or max_score <= 0:
            return {str(product_id): 0.0 for product_id, _ in sorted_recs}

        normalized = np.clip(scores / max_score, 0.0, 1.0)
        return {
            str(product_id): float(norm_score)
            for (product_id, _), norm_score in zip(sorted_recs, normalized)
        }
    
    def fit(self, interaction_df: pd.DataFrame, product_df: pd.DataFrame):
        """学習"""
        logger.info("Training hybrid recommender")
        
        self.interaction_df = interaction_df
        self.product_df = product_df
        
        # 協同フィルタリング
        try:
            self.cf_model.fit(interaction_df)
        except Exception as e:
            logger.error(f"CF training failed: {str(e)}")
        
        # コンテンツベース
        try:
            self.content_model.fit(product_df)
        except Exception as e:
            logger.error(f"Content-based training failed: {str(e)}")
        
        # 人気商品
        if 'product_id' in interaction_df.columns:
            score_col = 'purchase_count' if 'purchase_count' in interaction_df.columns else 'quantity'
            popular = interaction_df.groupby('product_id')[score_col].sum().nlargest(50)
            self.popular_items = popular.index.tolist()
        
        logger.info("Hybrid model training completed")
        
        return self
    
    def recommend(self, customer_id: str, top_k: int = 10, diversity_boost: float = 0.1) -> List[Dict[str, Any]]:
        """ハイブリッド推薦"""
        recommendations = {}
        
        # 協同フィルタリング推薦
        try:
            cf_recs = self.cf_model.recommend(customer_id, top_k * 2)
            for product_id, score in cf_recs:
                if product_id not in recommendations:
                    recommendations[product_id] = 0
                recommendations[product_id] += score * self.cf_weight
        except Exception as e:
            logger.warning(f"CF recommendation failed: {str(e)}")
        
        # ユーザーの購買履歴から好みの商品を取得
        if self.interaction_df is not None and 'customer_id' in self.interaction_df.columns:
            user_history = self.interaction_df[self.interaction_df['customer_id'] == customer_id]
            if len(user_history) > 0:
                # 購買済み商品から類似商品を推薦
                purchased_products = user_history['product_id'].unique()[:5]
                
                for product_id in purchased_products:
                    try:
                        content_recs = self.content_model.recommend(product_id, top_k)
                        for rec_product_id, score in content_recs:
                            if rec_product_id not in recommendations:
                                recommendations[rec_product_id] = 0
                            recommendations[rec_product_id] += score * self.content_weight
                    except Exception as e:
                        logger.warning(f"Content-based recommendation failed for {product_id}: {str(e)}")
        
        # 推薦が少ない場合は人気商品を追加
        if len(recommendations) < top_k:
            for product_id in self.popular_items[:top_k]:
                if product_id not in recommendations:
                    recommendations[product_id] = 0.5
        
        # スコア順にソート
        sorted_recs = sorted(recommendations.items(), key=lambda x: x[1], reverse=True)[:top_k]
        normalized_map = self._normalize_scores(sorted_recs)
        
        # 商品情報を追加
        result = []
        for product_id, score in sorted_recs:
            product_info = {
                'product_id': product_id,
                'score': float(normalized_map.get(str(product_id), 0.0)),
                'raw_score': float(score),
            }
            
            # 商品詳細を追加
            if self.product_df is not None and 'product_id' in self.product_df.columns:
                product_data = self.product_df[self.product_df['product_id'] == product_id]
                if len(product_data) > 0:
                    product_row = product_data.iloc[0]
                    if 'product_name' in product_row:
                        product_info['product_name'] = product_row['product_name']
                    if 'category_level1' in product_row:
                        product_info['category'] = product_row['category_level1']
                    if 'retail_price_jpy' in product_row:
                        product_info['price'] = float(product_row['retail_price_jpy'])
            
            result.append(product_info)
        
        return result
    
    def recommend_popular(self, top_k: int = 10, store_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """人気商品推薦（コールドスタート用）"""
        if store_id and 'store_id' in self.interaction_df.columns:
            # 店舗別人気商品
            store_data = self.interaction_df[self.interaction_df['store_id'] == store_id]
            if len(store_data) > 0:
                score_col = 'purchase_count' if 'purchase_count' in store_data.columns else 'quantity'
                popular = store_data.groupby('product_id')[score_col].sum().nlargest(top_k)
                popular_products = popular.index.tolist()
            else:
                popular_products = self.popular_items[:top_k]
        else:
            popular_products = self.popular_items[:top_k]
        
        # 商品情報を追加
        result = []
        for product_id in popular_products:
            product_info = {'product_id': product_id, 'score': 1.0}
            
            if self.product_df is not None and 'product_id' in self.product_df.columns:
                product_data = self.product_df[self.product_df['product_id'] == product_id]
                if len(product_data) > 0:
                    product_row = product_data.iloc[0]
                    if 'product_name' in product_row:
                        product_info['product_name'] = product_row['product_name']
                    if 'category_level1' in product_row:
                        product_info['category'] = product_row['category_level1']
                    if 'retail_price_jpy' in product_row:
                        product_info['price'] = float(product_row['retail_price_jpy'])
            
            result.append(product_info)
        
        return result
    
    def save(self, model_dir: Path):
        """モデル保存"""
        model_dir.mkdir(parents=True, exist_ok=True)
        
        with open(model_dir / 'hybrid_recommender.pkl', 'wb') as f:
            pickle.dump({
                'cf_model': self.cf_model,
                'content_model': self.content_model,
                'popular_items': self.popular_items,
                'cf_weight': self.cf_weight,
                'content_weight': self.content_weight
            }, f)
        
        logger.info(f"Recommender saved to {model_dir}")
    
    def load(self, model_dir: Path):
        """モデル読み込み"""
        with open(model_dir / 'hybrid_recommender.pkl', 'rb') as f:
            data = pickle.load(f)
            self.cf_model = data['cf_model']
            self.content_model = data['content_model']
            self.popular_items = data['popular_items']
            self.cf_weight = data['cf_weight']
            self.content_weight = data['content_weight']
        
        logger.info(f"Recommender loaded from {model_dir}")
