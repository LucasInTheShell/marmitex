from fastapi import APIRouter, status

from app.modules.auth.api.dependencies import AdminAccount
from app.modules.companies.api.dependencies import CompanyServiceDependency
from app.modules.companies.api.schemas import CompanyCreate, CompanyResponse

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyResponse])
async def list_companies(_: AdminAccount, service: CompanyServiceDependency):
    return await service.list()


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate, _: AdminAccount, service: CompanyServiceDependency
):
    return await service.create(payload.name.strip(), str(payload.email), payload.password)

