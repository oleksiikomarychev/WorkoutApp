from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class MovementType(str, Enum):
    compound = "compound"
    isolation = "isolation"


class Region(str, Enum):
    upper = "upper"
    lower = "lower"


class Muscle(str, Enum):
    # Chest
    PectoralisMajor = "PectoralisMajor"
    PectoralisMinor = "PectoralisMinor"
    SerratusAnterior = "SerratusAnterior"

    # Back
    LatissimusDorsi = "LatissimusDorsi"
    TrapeziusUpper = "TrapeziusUpper"
    TrapeziusMiddle = "TrapeziusMiddle"
    TrapeziusLower = "TrapeziusLower"
    RhomboidMajor = "RhomboidMajor"
    RhomboidMinor = "RhomboidMinor"
    ErectorSpinae = "ErectorSpinae"
    TeresMajor = "TeresMajor"
    TeresMinor = "TeresMinor"
    Infraspinatus = "Infraspinatus"

    # Shoulders
    DeltoidAnterior = "DeltoidAnterior"
    DeltoidLateral = "DeltoidLateral"
    DeltoidPosterior = "DeltoidPosterior"
    Supraspinatus = "Supraspinatus"
    Subscapularis = "Subscapularis"

    # Arms
    BicepsBrachiiShortHead = "BicepsBrachiiShortHead"
    BicepsBrachiiLongHead = "BicepsBrachiiLongHead"
    Brachialis = "Brachialis"
    Brachioradialis = "Brachioradialis"
    TricepsLongHead = "TricepsLongHead"
    TricepsLateralHead = "TricepsLateralHead"
    TricepsMedialHead = "TricepsMedialHead"
    ForearmFlexors = "ForearmFlexors"
    ForearmExtensors = "ForearmExtensors"

    # Legs
    GluteusMaximus = "GluteusMaximus"
    GluteusMedius = "GluteusMedius"
    GluteusMinimus = "GluteusMinimus"
    QuadricepsRectusFemoris = "QuadricepsRectusFemoris"
    QuadricepsVastusLateralis = "QuadricepsVastusLateralis"
    QuadricepsVastusMedialis = "QuadricepsVastusMedialis"
    QuadricepsVastusIntermedius = "QuadricepsVastusIntermedius"
    HamstringsBicepsFemoris = "HamstringsBicepsFemoris"
    HamstringsSemitendinosus = "HamstringsSemitendinosus"
    HamstringsSemimembranosus = "HamstringsSemimembranosus"
    AdductorLongus = "AdductorLongus"
    AdductorBrevis = "AdductorBrevis"
    AdductorMagnus = "AdductorMagnus"
    Gracilis = "Gracilis"
    Sartorius = "Sartorius"
    TensorFasciaeLatae = "TensorFasciaeLatae"
    GastrocnemiusMedialHead = "GastrocnemiusMedialHead"
    GastrocnemiusLateralHead = "GastrocnemiusLateralHead"
    Soleus = "Soleus"
    TibialisAnterior = "TibialisAnterior"

    # Core
    RectusAbdominis = "RectusAbdominis"
    ExternalOblique = "ExternalOblique"
    InternalOblique = "InternalOblique"
    TransversusAbdominis = "TransversusAbdominis"
    QuadratusLumborum = "QuadratusLumborum"

    # Neck
    Sternocleidomastoid = "Sternocleidomastoid"
    SpleniusCapitis = "SpleniusCapitis"
    LevatorScapulae = "LevatorScapulae"


class MuscleInfo(BaseModel):
    key: Muscle
    label: str
    group: str


class ExerciseListBase(BaseModel):
    name: str = Field(..., max_length=255)
    muscle_group: Optional[str] = None
    equipment: Optional[str] = None
    # Keep as strings for backward compatibility with DB; client may map to enum
    target_muscles: Optional[List[str]] = None
    synergist_muscles: Optional[List[str]] = None
    movement_type: Optional[MovementType] = None
    region: Optional[Region] = None


class ExerciseListCreate(ExerciseListBase):
    pass


class ExerciseList(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True


class ExerciseSet(BaseModel):
    id: Optional[int] = Field(None, description="ID of the set within the instance")
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[int] = Field(None, ge=1)
    intensity: Optional[int] = Field(None)
    effort: Optional[float] = Field(None)

    class Config:
        extra = "allow"  # keep extra fields like reps/rpe/order etc.


class ExerciseSetUpdate(BaseModel):
    weight: Optional[float] = Field(None, ge=0)
    volume: Optional[int] = Field(None, ge=1)
    reps: Optional[int] = Field(None, ge=0)
    rpe: Optional[float] = Field(None, ge=0)
    order: Optional[int] = Field(None, ge=0)
    intensity: Optional[int] = Field(None)
    effort: Optional[float] = Field(None)

    class Config:
        extra = "allow"


class ExerciseInstanceBase(BaseModel):
    exercise_list_id: int
    sets: List[ExerciseSet]
    notes: Optional[str] = None
    order: Optional[int] = None

    class Config:
        from_attributes = True


class ExerciseInstanceCreate(ExerciseInstanceBase):
    user_max_id: Optional[int] = None


class ExerciseInstance(ExerciseInstanceBase):
    id: int
    workout_id: Optional[int] = None
    user_max_id: Optional[int] = None

    class Config:
        from_attributes = True


class ExerciseInstanceResponse(ExerciseInstanceBase):
    id: int
    workout_id: Optional[int] = None
    user_max_id: Optional[int] = None

    class Config:
        from_attributes = True


class ExerciseListResponse(ExerciseListBase):
    id: int

    class Config:
        from_attributes = True
