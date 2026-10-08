from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .models import SessionLocal
from .schemas import (
    Food,
    FoodResponse,
    Medication,
    MedicationResponse,
    SessionData,
    SessionDataResponse,
    Supplement,
    SupplementResponse,
)
from .services import (
    create_food,
    create_medication,
    create_session,
    create_supplement,
    delete_food,
    delete_medication,
    delete_session,
    delete_supplement,
    get_all_food,
    get_all_medications,
    get_all_sessions,
    get_all_supplements,
    get_food,
    get_medication,
    get_session,
    get_session_by_applied_plan_workout_id,
    get_session_by_workout_id,
    get_sessions_by_user_id,
    get_supplement,
    update_food,
    update_medication,
    update_session,
    update_supplement,
)

supplements_router = APIRouter(prefix="/supplements")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@supplements_router.post("/food", response_model=FoodResponse, status_code=status.HTTP_201_CREATED)
def create_food_endpoint(payload: Food, db: Session = Depends(get_db)):
    food = create_food(db, payload)
    return FoodResponse(
        id=food.id,
        name=food.name,
        unit=food.unit,
        dosage=food.dosage,
        calories=food.calories,
        proteins=food.proteins,
        fats=food.fats,
        carbs=food.carbs,
        weight_g=food.weight_g,
        created_at=food.created_at.isoformat()
    )

@supplements_router.get("/food/{food_id}", response_model=FoodResponse)
def get_food_endpoint(food_id: int, db: Session = Depends(get_db)):
    food = get_food(db, food_id)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return FoodResponse(
        id=food.id,
        name=food.name,
        unit=food.unit,
        dosage=food.dosage,
        calories=food.calories,
        proteins=food.proteins,
        fats=food.fats,
        carbs=food.carbs,
        weight_g=food.weight_g,
        created_at=food.created_at.isoformat()
    )

@supplements_router.get("/food", response_model=list[FoodResponse])
def get_all_food_endpoint(db: Session = Depends(get_db)):
    foods = get_all_food(db)
    return [
        FoodResponse(
            id=f.id,
            name=f.name,
            unit=f.unit,
            dosage=f.dosage,
            calories=f.calories,
            proteins=f.proteins,
            fats=f.fats,
            carbs=f.carbs,
            weight_g=f.weight_g,
            created_at=f.created_at.isoformat()
        )
        for f in foods
    ]

@supplements_router.put("/food/{food_id}", response_model=FoodResponse)
def update_food_endpoint(food_id: int, payload: Food, db: Session = Depends(get_db)):
    food = update_food(db, food_id, payload)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return FoodResponse(
        id=food.id,
        name=food.name,
        unit=food.unit,
        dosage=food.dosage,
        calories=food.calories,
        proteins=food.proteins,
        fats=food.fats,
        carbs=food.carbs,
        weight_g=food.weight_g,
        created_at=food.created_at.isoformat()
    )

@supplements_router.delete("/food/{food_id}")
def delete_food_endpoint(food_id: int, db: Session = Depends(get_db)):
    result = delete_food(db, food_id)
    if not result:
        raise HTTPException(status_code=404, detail="Food not found")
    return {"deleted": True}

@supplements_router.post("/supplement", response_model=SupplementResponse, status_code=status.HTTP_201_CREATED)
def create_supplement_endpoint(payload: Supplement, db: Session = Depends(get_db)):
    supplement = create_supplement(db, payload)
    return SupplementResponse(
        id=supplement.id,
        name=supplement.name,
        unit=supplement.unit,
        dosage=supplement.dosage,
        created_at=supplement.created_at.isoformat()
    )

@supplements_router.get("/supplement/{supplement_id}", response_model=SupplementResponse)
def get_supplement_endpoint(supplement_id: int, db: Session = Depends(get_db)):
    supplement = get_supplement(db, supplement_id)
    if not supplement:
        raise HTTPException(status_code=404, detail="Supplement not found")
    return SupplementResponse(
        id=supplement.id,
        name=supplement.name,
        unit=supplement.unit,
        dosage=supplement.dosage,
        created_at=supplement.created_at.isoformat()
    )

@supplements_router.get("/supplement", response_model=list[SupplementResponse])
def get_all_supplements_endpoint(db: Session = Depends(get_db)):
    supplements = get_all_supplements(db)
    return [
        SupplementResponse(
            id=s.id,
            name=s.name,
            unit=s.unit,
            dosage=s.dosage,
            created_at=s.created_at.isoformat()
        )
        for s in supplements
    ]

@supplements_router.put("/supplement/{supplement_id}", response_model=SupplementResponse)
def update_supplement_endpoint(supplement_id: int, payload: Supplement, db: Session = Depends(get_db)):
    supplement = update_supplement(db, supplement_id, payload)
    if not supplement:
        raise HTTPException(status_code=404, detail="Supplement not found")
    return SupplementResponse(
        id=supplement.id,
        name=supplement.name,
        unit=supplement.unit,
        dosage=supplement.dosage,
        created_at=supplement.created_at.isoformat()
    )

@supplements_router.delete("/supplement/{supplement_id}")
def delete_supplement_endpoint(supplement_id: int, db: Session = Depends(get_db)):
    result = delete_supplement(db, supplement_id)
    if not result:
        raise HTTPException(status_code=404, detail="Supplement not found")
    return {"deleted": True}

@supplements_router.post("/medication", response_model=MedicationResponse, status_code=status.HTTP_201_CREATED)
def create_medication_endpoint(payload: Medication, db: Session = Depends(get_db)):
    medication = create_medication(db, payload)
    return MedicationResponse(
        id=medication.id,
        name=medication.name,
        unit=medication.unit,
        dosage=medication.dosage,
        half_life_hours=medication.half_life_hours,
        concentration=medication.concentration,
        created_at=medication.created_at.isoformat()
    )

@supplements_router.get("/medication/{medication_id}", response_model=MedicationResponse)
def get_medication_endpoint(medication_id: int, db: Session = Depends(get_db)):
    medication = get_medication(db, medication_id)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    return MedicationResponse(
        id=medication.id,
        name=medication.name,
        unit=medication.unit,
        dosage=medication.dosage,
        half_life_hours=medication.half_life_hours,
        concentration=medication.concentration,
        created_at=medication.created_at.isoformat()
    )

@supplements_router.get("/medication", response_model=list[MedicationResponse])
def get_all_medications_endpoint(db: Session = Depends(get_db)):
    medications = get_all_medications(db)
    return [
        MedicationResponse(
            id=m.id,
            name=m.name,
            unit=m.unit,
            dosage=m.dosage,
            half_life_hours=m.half_life_hours,
            concentration=m.concentration,
            created_at=m.created_at.isoformat()
        )
        for m in medications
    ]

@supplements_router.put("/medication/{medication_id}", response_model=MedicationResponse)
def update_medication_endpoint(medication_id: int, payload: Medication, db: Session = Depends(get_db)):
    medication = update_medication(db, medication_id, payload)
    if not medication:
        raise HTTPException(status_code=404, detail="Medication not found")
    return MedicationResponse(
        id=medication.id,
        name=medication.name,
        unit=medication.unit,
        dosage=medication.dosage,
        half_life_hours=medication.half_life_hours,
        concentration=medication.concentration,
        created_at=medication.created_at.isoformat()
    )

@supplements_router.delete("/medication/{medication_id}")
def delete_medication_endpoint(medication_id: int, db: Session = Depends(get_db)):
    result = delete_medication(db, medication_id)
    if not result:
        raise HTTPException(status_code=404, detail="Medication not found")
    return {"deleted": True}

@supplements_router.post("/session", response_model=SessionDataResponse, status_code=status.HTTP_201_CREATED)
def create_session_endpoint(payload: SessionData, db: Session = Depends(get_db)):
    session = create_session(db, payload)
    return SessionDataResponse(
        id=session.id,
        user_id=session.user_id,
        session_id=session.session_id,
        entries=session.entries,
        workout_id=session.workout_id,
        applied_plan_workout_id=session.applied_plan_workout_id,
        date=session.date.isoformat()
    )

@supplements_router.get("/session/{session_id}", response_model=SessionDataResponse)
def get_session_endpoint(session_id: str, db: Session = Depends(get_db)):
    session = get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDataResponse(
        id=session.id,
        user_id=session.user_id,
        session_id=session.session_id,
        entries=session.entries,
        workout_id=session.workout_id,
        applied_plan_workout_id=session.applied_plan_workout_id,
        date=session.date.isoformat()
    )

@supplements_router.get("/session", response_model=list[SessionDataResponse])
def get_all_sessions_endpoint(db: Session = Depends(get_db)):
    sessions = get_all_sessions(db)
    return [
        SessionDataResponse(
            id=s.id,
            user_id=s.user_id,
            session_id=s.session_id,
            entries=s.entries,
            workout_id=s.workout_id,
            applied_plan_workout_id=s.applied_plan_workout_id,
            date=s.date.isoformat()
        )
        for s in sessions
    ]

@supplements_router.get("/session/user/{user_id}", response_model=list[SessionDataResponse])
def get_sessions_by_user_id_endpoint(user_id: int, db: Session = Depends(get_db)):
    sessions = get_sessions_by_user_id(db, user_id)
    return [
        SessionDataResponse(
            id=s.id,
            user_id=s.user_id,
            session_id=s.session_id,
            entries=s.entries,
            workout_id=s.workout_id,
            applied_plan_workout_id=s.applied_plan_workout_id,
            date=s.date.isoformat()
        )
        for s in sessions
    ]

@supplements_router.get("/session/workout/{workout_id}", response_model=SessionDataResponse)
def get_session_by_workout_id_endpoint(workout_id: int, db: Session = Depends(get_db)):
    session = get_session_by_workout_id(db, workout_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDataResponse(
        id=session.id,
        user_id=session.user_id,
        session_id=session.session_id,
        entries=session.entries,
        workout_id=session.workout_id,
        applied_plan_workout_id=session.applied_plan_workout_id,
        date=session.date.isoformat()
    )

@supplements_router.get("/session/applied-plan-workout/{applied_plan_workout_id}", response_model=SessionDataResponse)
def get_session_by_applied_plan_workout_id_endpoint(applied_plan_workout_id: int, db: Session = Depends(get_db)):
    session = get_session_by_applied_plan_workout_id(db, applied_plan_workout_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDataResponse(
        id=session.id,
        user_id=session.user_id,
        session_id=session.session_id,
        entries=session.entries,
        workout_id=session.workout_id,
        applied_plan_workout_id=session.applied_plan_workout_id,
        date=session.date.isoformat()
    )

@supplements_router.put("/session/{session_id}", response_model=SessionDataResponse)
def update_session_endpoint(session_id: str, payload: SessionData, db: Session = Depends(get_db)):
    session = update_session(db, session_id, payload)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionDataResponse(
        id=session.id,
        user_id=session.user_id,
        session_id=session.session_id,
        entries=session.entries,
        workout_id=session.workout_id,
        applied_plan_workout_id=session.applied_plan_workout_id,
        date=session.date.isoformat()
    )

@supplements_router.delete("/session/{session_id}")
def delete_session_endpoint(session_id: str, db: Session = Depends(get_db)):
    result = delete_session(db, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}