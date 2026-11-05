from pydantic import BaseModel, ConfigDict


class ColumnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    unit: str


class ReportRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    label: str
    values: dict[str, float]


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report: str
    title: str
    grouping: str
    columns: list[ColumnOut]
    rows: list[ReportRowOut]
    totals: dict[str, float]


class GroupingOut(BaseModel):
    name: str
    title: str


class ReportInfo(BaseModel):
    name: str
    title: str
    groupings: list[GroupingOut]
