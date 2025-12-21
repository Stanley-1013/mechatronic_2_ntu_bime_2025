"""
Statistics Models
統計模型
"""
from pydantic import BaseModel, Field
from typing import Optional


class SampleStats(BaseModel):
    """
    樣本統計資料
    用於即時監控和分析
    """
    count: int = Field(..., description="樣本數量")
    mean: float = Field(..., description="平均值")
    std: float = Field(..., description="標準差")
    min_value: float = Field(..., description="最小值")
    max_value: float = Field(..., description="最大值")
    median: Optional[float] = Field(None, description="中位數")

    class Config:
        json_schema_extra = {
            "example": {
                "count": 1000,
                "mean": 0.5,
                "std": 0.1,
                "min_value": 0.2,
                "max_value": 0.8,
                "median": 0.51
            }
        }
