from uuid import UUID

from fastapi import APIRouter, status

from app.modules.auth.api.dependencies import AdminAccount, CompanyAccount
from app.modules.companies.api.dependencies import CompanyServiceDependency
from app.modules.companies.api.schemas import (
    CompanyCreate,
    CompanyResponse,
    MealScheduleCreate,
    MealScheduleResponse,
    MealScheduleUpdate,
)
from app.modules.companies.domain.entities import MealScheduleDraft

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[CompanyResponse])
async def list_companies(_: AdminAccount, service: CompanyServiceDependency):
    return await service.list()


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    payload: CompanyCreate, _: AdminAccount, service: CompanyServiceDependency
):
    schedules = [
        MealScheduleDraft(
            label=schedule.label.strip(),
            meal_time=schedule.meal_time,
            weekdays=schedule.weekdays,
            sort_order=schedule.sort_order,
        )
        for schedule in payload.meal_schedules
    ]
    return await service.create(
        payload.name.strip(), str(payload.email), payload.password, schedules
    )


@router.get("/me", response_model=CompanyResponse)
async def own_company(account: CompanyAccount, service: CompanyServiceDependency):
    return await service.by_id(account.company_id)


@router.post(
    "/{company_id}/meal-schedules",
    response_model=MealScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_meal_schedule(
    company_id: UUID,
    payload: MealScheduleCreate,
    _: AdminAccount,
    service: CompanyServiceDependency,
):
    return await service.add_meal_schedule(
        company_id,
        MealScheduleDraft(
            label=payload.label.strip(),
            meal_time=payload.meal_time,
            weekdays=payload.weekdays,
            sort_order=payload.sort_order,
        ),
    )


@router.patch(
    "/{company_id}/meal-schedules/{schedule_id}",
    response_model=MealScheduleResponse,
)
async def update_meal_schedule(
    company_id: UUID,
    schedule_id: UUID,
    payload: MealScheduleUpdate,
    _: AdminAccount,
    service: CompanyServiceDependency,
):
    return await service.update_meal_schedule(
        company_id,
        schedule_id,
        payload.label.strip() if payload.label is not None else None,
        payload.meal_time,
        payload.weekdays,
        payload.active,
        payload.sort_order,
    )

