#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import mariadb

class DBHandler:
    def __init__(self, db_config):
        allow = {"host","port","user","password","database","unix_socket","ssl","connect_timeout","autocommit"}
        self.db_config = {k:v for k,v in db_config.items() if k in allow}

    def get_all_products(self):
        """
        Product 테이블(product_id, product_name, price, quantity)에서 전체 조회
        """
        conn = None
        cursor = None
        try:
            conn = mariadb.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT product_id, product_name, price, quantity FROM Product")
            rows = cursor.fetchall()

            results = []
            for row in rows:
                results.append({
                    'product_id': row[0],
                    'product_name': row[1],
                    'price': float(row[2]) if row[2] is not None else 0.0,
                    'quantity': row[3]
                })
            return results
        except mariadb.Error as e:
            raise Exception(f"DB 오류: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_product_by_id(self, product_id):
        """
        단건 조회
        """
        conn = None
        cursor = None
        try:
            conn = mariadb.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT product_name, price, quantity FROM Product WHERE product_id = ?", (product_id,))
            result = cursor.fetchone()

            if result:
                return {
                    'product_name': result[0],
                    'price': float(result[1]) if result[1] is not None else 0.0,
                    'quantity': result[2]
                }
            return None
        except mariadb.Error as e:
            raise Exception(f"DB 오류: {e}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
