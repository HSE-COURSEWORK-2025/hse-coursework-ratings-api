import logging
from typing import List
from fastapi import APIRouter, HTTPException
from app.services.findDataOutliers import analyze_and_return_json, generate_random_data
from app.models.getData import DataElementSchema, DataType, AnalyzedDataSchema


logger = logging.getLogger("get_data_routers")
api_v2_get_data_router = APIRouter(prefix="/getData")


@api_v2_get_data_router.get(
    "/getRawData",
    status_code=200,
    response_model=List[DataElementSchema],
    tags=["get_data"],
)
async def getRawData(data_type: DataType) -> List[DataElementSchema]:
    try:
        generated_data = generate_random_data(data_type)
        return generated_data

    except Exception as e:
        logger.error(f"Error generating data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@api_v2_get_data_router.get(
    "/getAnalyzedData",
    status_code=200,
    response_model=AnalyzedDataSchema,
    tags=["get_data"],
)
async def getAnalyzedData(data_type: DataType) -> AnalyzedDataSchema:
    try:
        generated_data = generate_random_data(data_type)
        result = analyze_and_return_json(generated_data)
        return AnalyzedDataSchema.model_validate(result)

    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
