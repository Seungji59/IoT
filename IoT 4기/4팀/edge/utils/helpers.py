# 유틸리티 헬퍼 함수 모듈
from typing import Tuple

from config import CONFIDENCE_THRESHOLD


def calculate_confidence_score(error: float) -> int:
    """
    오차 값을 신뢰도 점수로 변환
    
    Args:
        error: 평균 오차 (미터)
        
    Returns:
        int: 신뢰도 점수 (0-10)
    """
    score = int(max(0, 10 - error * 3))
    return score


def is_confident(error: float) -> bool:
    """
    신뢰도 판별
    
    Args:
        error: 평균 오차 (미터)
        
    Returns:
        bool: 신뢰 가능 여부
    """
    score = calculate_confidence_score(error)
    return score > CONFIDENCE_THRESHOLD


def format_coordinates(grid_x: int, grid_y: int, resolution: float = 0.1) -> Tuple[float, float]:
    """
    그리드 좌표를 포맷팅된 미터 좌표로 변환
    
    Args:
        grid_x: 그리드 X 좌표
        grid_y: 그리드 Y 좌표
        resolution: 그리드 해상도 (기본: 0.1m)
        
    Returns:
        Tuple[float, float]: (x_meter, y_meter) - 소수점 둘째자리까지
    """
    x_meter = float(f"{grid_x * resolution + resolution / 2:.2f}")
    y_meter = float(f"{grid_y * resolution + resolution / 2:.2f}")
    return x_meter, y_meter