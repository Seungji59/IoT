#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mariadb
import pandas as pd
from mlxtend.frequent_patterns import apriori, association_rules


def _norm_gender(g):
    if g is None: return "U"
    g = str(g).strip().upper()
    if g in ("M", "MALE", "남", "남성"): return "M"
    if g in ("F", "FEMALE", "여", "여성"): return "F"
    return "U"


def _norm_age(age):
    if pd.isna(age):
        return "0s"
    age = str(age).strip()
    if age.endswith("대"):
        num_part = age[:-1]
        if num_part.isdigit():
            return f"{num_part}s"
    return age  # 이미 "10s" 형태면 그대로 사용


class Recommender:
    def __init__(self, db_config):
        allow = {"host", "port", "user", "password", "database", "unix_socket", "ssl", "connect_timeout"}
        self.db_config = {k: v for k, v in db_config.items() if k in allow}

        self.product_df = None
        self.rules = None
        self.popular_products = None
        self.items_by_payment = {}
        self._train_models()

    def _conn(self):
        return mariadb.connect(**self.db_config)

    def _load_data(self):
        with self._conn() as conn:
            self.product_df = pd.read_sql(
                "SELECT product_id AS product_code, product_name AS name, price FROM product",
                conn
            )
            pay_df = pd.read_sql(
                "SELECT customerid AS payment_id, cartid AS user_id, gender, age_group AS age, product_id FROM purchase",
                conn
            )
        self.product_df["product_code"] = self.product_df["product_code"].astype(str)
        pay_df["product_id"] = pay_df["product_id"].astype(str)
        return pay_df

    def _prepare_data(self, pay_df):
        grouped = pay_df.groupby("payment_id")
        transactions_demog = []
        items_by_payment = {}

        universe_products = set(self.product_df["product_code"].tolist())
        universe_tokens = set()

        for pid, g in grouped:
            prods = set(g["product_id"].tolist())
            gender = _norm_gender(g["gender"].iloc[0])
            agecat = _norm_age(g["age"].iloc[0])

            tokens = {f"gender_{gender}", agecat}
            universe_tokens.update(tokens)

            txn_full = prods.union(tokens)
            transactions_demog.append(txn_full)

            items_by_payment[pid] = set(prods)

        all_items = sorted(list(universe_products.union(universe_tokens)))
        te = pd.DataFrame(
            [{col: (col in items) for col in all_items} for items in transactions_demog],
            dtype=bool
        )
        self.items_by_payment = items_by_payment
        return te, pay_df

    def _train_apriori(self, te):
        try:
            # 더 낮은 최소 지지도로 시작
            frequent_itemsets = apriori(te, min_support=0.001, use_colnames=True)
            if frequent_itemsets.empty:
                print("[추천 시스템] 빈발 항목집합이 없습니다. 최소 지지도를 더 낮춰보세요.")
                self.rules = None
                return
            
            print(f"[추천 시스템] 빈발 항목집합 발견: {len(frequent_itemsets)}개")
            
            # 더 낮은 최소 리프트 값 사용
            rules = association_rules(frequent_itemsets, metric="lift", min_threshold=0.5)
            if rules.empty:
                print("[추천 시스템] 연관 규칙이 없습니다. 임계값을 낮춰보세요.")
                self.rules = None
                return
                
            self.rules = rules
            print(f"[추천 시스템] 연관 규칙 생성 완료: {len(rules)}개")
            
        except Exception as e:
            print(f"[추천 시스템] Apriori 학습 중 오류: {e}")
            self.rules = None

    def _get_candidates(self, item, gender, age):
        if self.rules is None:
            return set()
        gender_tok = f"gender_{_norm_gender(gender)}"
        age_cat = _norm_age(age)
        demo_set = frozenset([item, gender_tok, age_cat])

        ants = self.rules['antecedents']
        m_demo = ants.apply(lambda s: demo_set.issubset(s))
        m_prod = ants.apply(lambda s: frozenset([item]).issubset(s))

        c1 = set().union(*self.rules[m_demo]['consequents']) if m_demo.any() else set()
        c2 = set().union(*self.rules[m_prod]['consequents']) if m_prod.any() else set()

        prod_set = set(self.product_df['product_code'].tolist())
        return (c1.union(c2)).intersection(prod_set)

    def _get_metrics(self, item, gender, age, conseq):
        if self.rules is None:
            return 0.0, 0.0, 0.0
        gender_tok = f"gender_{_norm_gender(gender)}"
        age_cat = _norm_age(age)
        demo_set = frozenset([item, gender_tok, age_cat])

        df1 = self.rules[self.rules['antecedents'] == demo_set]
        if not df1.empty:
            df1 = df1[df1['consequents'].apply(lambda s: conseq in s)]
            if not df1.empty:
                row = df1.iloc[0]
                return row['support'], row['confidence'], row['lift']

        df2 = self.rules[self.rules['antecedents'] == frozenset([item])]
        df2 = df2[df2['consequents'].apply(lambda s: conseq in s)]
        if not df2.empty:
            row = df2.iloc[0]
            return row['support'], row['confidence'], row['lift']

        return 0.0, 0.0, 0.0

    def _train_models(self):
        pay_df = self._load_data()
        if pay_df.empty or self.product_df.empty:
            print("[추천 시스템] 데이터가 없어 추천 모델 학습을 건너뜁니다.")
            self.rules = None
            self.popular_products = []
            return

        print(f"[추천 시스템] 구매 데이터 로드 완료: {len(pay_df)}건")
        print(f"[추천 시스템] 상품 데이터 로드 완료: {len(self.product_df)}건")
        
        te, pay_df_filtered = self._prepare_data(pay_df)
        print(f"[추천 시스템] 트랜잭션 데이터 준비 완료: {len(te)}건")
        
        self._train_apriori(te)
        if self.rules is not None:
            print(f"[추천 시스템] 연관 규칙 학습 완료: {len(self.rules)}개 규칙")
        else:
            print("[추천 시스템] 연관 규칙 학습 실패 (데이터 부족)")

        counts = {}
        for items in self.items_by_payment.values():
            for p in items:
                counts[p] = counts.get(p, 0) + 1
        self.popular_products = [p for p, _ in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
        print(f"[추천 시스템] 인기 상품 순위: {self.popular_products[:10]}")

    def recommend(self, cart, gender, age):
        print(f"[추천 시스템] 입력 - 장바구니: {cart}, 성별: {gender}, 나이: {age}")
        
        # 장바구니가 비어있으면 인기 상품 추천
        if not cart:
            return self.popular_products[:3]
        
        # 장바구니 상품 정규화
        normalized_cart = []
        for item in cart:
            if isinstance(item, str) and item.startswith('product_'):
                item = item.replace('product_', '')
            normalized_cart.append(str(item))
        
        print(f"[추천 시스템] 정규화된 장바구니: {normalized_cart}")
        
        # 모든 상품에 대한 추천 후보를 수집하고 점수 합산
        candidate_scores = {}
        
        for item in normalized_cart:
            print(f"[추천 시스템] 처리 중인 상품: {item}")
            
            cands = self._get_candidates(item, gender, age)
            print(f"[추천 시스템] 연관 규칙 후보: {cands}")
            
            for cand in cands:
                # 장바구니에 이미 있는 상품은 제외
                if cand in normalized_cart:
                    continue
                    
                support, confidence, lift = self._get_metrics(item, gender, age, cand)
                score = confidence * lift
                
                if cand in candidate_scores:
                    # 기존 점수에 가중 평균 적용
                    old_score, count = candidate_scores[cand]
                    new_score = (old_score * count + score) / (count + 1)
                    candidate_scores[cand] = (new_score, count + 1)
                else:
                    candidate_scores[cand] = (score, 1)
                
                print(f"[점수 계산] {item} → {cand}: support={support:.3f}, confidence={confidence:.3f}, lift={lift:.3f}, 점수={score:.3f}, 누적점수={candidate_scores[cand][0]:.3f}")
        
        # 점수순으로 정렬하여 상위 3개 선택
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1][0], reverse=True)
        recommendations = [cand for cand, _ in sorted_candidates[:3]]
        
        # 부족한 부분은 인기 상품으로 채우기
        for pop in self.popular_products:
            if len(recommendations) >= 3:
                break
            if pop not in recommendations and pop not in normalized_cart:
                recommendations.append(pop)
        
        final_recommendations = recommendations[:3]
        print(f"[추천 시스템] 최종 추천: {final_recommendations}")
        
        return final_recommendations
    
    def _get_unified_recommendations(self, cart, gender, age):
        """전체 장바구니를 고려한 통합 추천"""
        print(f"[추천 시스템] 통합 추천 시작 - 장바구니: {cart}")
        
        # 모든 상품에 대한 추천 후보를 수집하고 점수 합산
        candidate_scores = {}
        
        for item in cart:
            cands = self._get_candidates(item, gender, age)
            
            for cand in cands:
                support, confidence, lift = self._get_metrics(item, gender, age, cand)
                score = confidence * lift
                
                if cand in candidate_scores:
                    # 기존 점수에 가중 평균 적용
                    old_score, count = candidate_scores[cand]
                    new_score = (old_score * count + score) / (count + 1)
                    candidate_scores[cand] = (new_score, count + 1)
                else:
                    candidate_scores[cand] = (score, 1)
                
                print(f"[통합 점수] {item} → {cand}: 개별점수={score:.3f}, 누적점수={candidate_scores[cand][0]:.3f}")
        
        # 장바구니에 없는 상품만 필터링하고 점수순 정렬
        filtered_candidates = [
            (cand, score) for cand, (score, count) in candidate_scores.items() 
            if cand not in cart
        ]
        
        # 점수순으로 정렬
        sorted_candidates = sorted(filtered_candidates, key=lambda x: x[1], reverse=True)
        unified_recommendations = [cand for cand, _ in sorted_candidates[:3]]
        
        # 부족한 부분은 인기 상품으로 채우기
        for pop in self.popular_products:
            if len(unified_recommendations) >= 3:  # 통합 추천은 3개까지
                break
            if pop not in unified_recommendations and pop not in cart:
                unified_recommendations.append(pop)
        
        print(f"[추천 시스템] 통합 추천 결과: {unified_recommendations[:3]}")
        return unified_recommendations[:3]
