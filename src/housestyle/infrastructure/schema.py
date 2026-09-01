import typing

import pydantic

from ..domain.diagnostic import Severity


SEVERITIES = {severity.name.lower(): severity for severity in Severity}


class RuleTable(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra='allow', frozen=True)

    severity: str | None = None

    @property
    def resolved_severity(self) -> Severity | None:
        return SEVERITIES.get(self.severity) if self.severity else None

    @property
    def options(self) -> dict[str, object]:
        return dict(self.__pydantic_extra__ or {})


RuleEntry = typing.Annotated[bool | str | RuleTable, pydantic.Field(union_mode='left_to_right')]


class ProjectSection(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True, populate_by_name=True)

    line_width: int = pydantic.Field(default=120, alias='line-width', gt=0)
    exclude: tuple[str, ...] = ()


class ConfigFile(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True)

    housestyle: ProjectSection = pydantic.Field(default_factory=ProjectSection)
    rules: dict[str, RuleEntry] = pydantic.Field(default_factory=dict)

    @classmethod
    def parse(cls, raw: typing.Mapping[str, object]) -> 'ConfigFile':
        try:
            return cls.model_validate(raw)
        except pydantic.ValidationError:
            return cls()


class ValeAlert(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(frozen=True, extra='ignore')

    check: str = pydantic.Field(alias='Check')
    message: str = pydantic.Field(alias='Message')
    line: int = pydantic.Field(alias='Line', ge=1)
    span: tuple[int, int] = pydantic.Field(default=(1, 1), alias='Span')
    severity: str = pydantic.Field(default='error', alias='Severity')

    @property
    def resolved_severity(self) -> Severity:
        return SEVERITIES.get(self.severity, Severity.ERROR)


class ValeReport(pydantic.RootModel[dict[str, list[ValeAlert]]]):
    @classmethod
    def parse(cls, payload: str) -> tuple[ValeAlert, ...]:
        try:
            parsed = cls.model_validate_json(payload or '{}')
        except pydantic.ValidationError:
            return ()
        return tuple(alert for alerts in parsed.root.values() for alert in alerts)
