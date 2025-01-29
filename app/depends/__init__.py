from typing import Annotated

from fastapi import Depends

from app.manager import PipelineSession, get_pipeline_session

DependPipelineSession = Annotated[PipelineSession, Depends(get_pipeline_session)]
