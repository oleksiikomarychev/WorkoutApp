from pydantic import BaseModel, Field


class ParamsSets(BaseModel):
    intensity: int | None = Field(default=None, ge=0, le=110)
    effort: int | None = Field(default=None, ge=1, le=10)
    volume: int | None = Field(default=None, ge=1)
    working_weight: float | None = Field(default=None, exclude=True)


class ExerciseScheduleItem(BaseModel):
    exercise_id: int
    sets: list[ParamsSets]

    class Config:
        from_attributes = True

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)

        if "sets" in data and data["sets"]:
            for set_item in data["sets"]:
                set_item.pop("working_weight", None)
        return data
