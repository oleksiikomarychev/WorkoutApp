from .models import FoodModel, MedicationModel, SessionDataModel, SessionLocal, SupplementModel
from .schemas import Food, Medication, SessionData, Supplement


def create_food(db: SessionLocal, payload: Food) -> FoodModel:
    food = FoodModel(**payload.dict())
    db.add(food)
    db.commit()
    db.refresh(food)
    return food

def get_food(db: SessionLocal, food_id: int) -> FoodModel:
    return db.query(FoodModel).filter(FoodModel.id == food_id).first()

def get_all_food(db: SessionLocal) -> list[FoodModel]:
    return db.query(FoodModel).all()

def update_food(db: SessionLocal, food_id: int, payload: Food) -> FoodModel:
    food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
    if food:
        for key, value in payload.dict().items():
            setattr(food, key, value)
        db.commit()
        db.refresh(food)
    return food

def delete_food(db: SessionLocal, food_id: int) -> bool:
    food = db.query(FoodModel).filter(FoodModel.id == food_id).first()
    if food:
        db.delete(food)
        db.commit()
        return True
    return False

def create_supplement(db: SessionLocal, payload: Supplement) -> Supplement:
    supplement = SupplementModel(**payload.dict())
    db.add(supplement)
    db.commit()
    db.refresh(supplement)
    return supplement

def get_supplement(db: SessionLocal, supplement_id: int) -> SupplementModel:
    return db.query(SupplementModel).filter(SupplementModel.id == supplement_id).first()

def get_all_supplements(db: SessionLocal) -> list[SupplementModel]:
    return db.query(SupplementModel).all()

def update_supplement(db: SessionLocal, supplement_id: int, payload: Supplement) -> SupplementModel:
    supplement = db.query(SupplementModel).filter(SupplementModel.id == supplement_id).first()
    if supplement:
        for key, value in payload.dict().items():
            setattr(supplement, key, value)
        db.commit()
        db.refresh(supplement)
    return supplement

def delete_supplement(db: SessionLocal, supplement_id: int) -> bool:
    supplement = db.query(SupplementModel).filter(SupplementModel.id == supplement_id).first()
    if supplement:
        db.delete(supplement)
        db.commit()
        return True
    return False

def create_medication(db: SessionLocal, payload: Medication) -> Medication:
    medication = MedicationModel(**payload.dict())
    db.add(medication)
    db.commit()
    db.refresh(medication)
    return medication

def get_medication(db: SessionLocal, medication_id: int) -> Medication:
    return db.query(MedicationModel).filter(MedicationModel.id == medication_id).first()

def get_all_medications(db: SessionLocal) -> list[Medication]:
    return db.query(MedicationModel).all()

def update_medication(db: SessionLocal, medication_id: int, payload: Medication) -> Medication:
    medication = db.query(MedicationModel).filter(MedicationModel.id == medication_id).first()
    if medication:
        for key, value in payload.dict().items():
            setattr(medication, key, value)
        db.commit()
        db.refresh(medication)
    return medication

def delete_medication(db: SessionLocal, medication_id: int) -> bool:
    medication = db.query(MedicationModel).filter(MedicationModel.id == medication_id).first()
    if medication:
        db.delete(medication)
        db.commit()
        return True
    return False

def create_session(db: SessionLocal, payload: SessionData) -> SessionData:
    session = SessionDataModel(**payload.dict())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_session(db: SessionLocal, session_id: str) -> SessionData:
    session = db.query(SessionDataModel).filter(SessionDataModel.session_id == session_id).first()
    return session

def get_session_by_user_id(db: SessionLocal, user_id: int) -> SessionData:
    session = db.query(SessionDataModel).filter(SessionDataModel.user_id == user_id).first()
    return session

def get_session_by_workout_id(db: SessionLocal, workout_id: int) -> SessionData:
    return db.query(SessionDataModel).filter(SessionDataModel.workout_id == workout_id).first()

def get_session_by_applied_plan_workout_id(db: SessionLocal, applied_plan_workout_id: int) -> SessionData:
    return db.query(SessionDataModel).filter(SessionDataModel.applied_plan_workout_id == applied_plan_workout_id).first()

def get_all_sessions(db: SessionLocal) -> list[SessionData]:
    return db.query(SessionDataModel).all()

def get_sessions_by_user_id(db: SessionLocal, user_id: int) -> list[SessionData]:
    return db.query(SessionDataModel).filter(SessionDataModel.user_id == user_id).all()

def update_session(db: SessionLocal, session_id: str, payload: SessionData) -> SessionData:
    session = db.query(SessionDataModel).filter(SessionDataModel.session_id == session_id).first()
    if session:
        for key, value in payload.dict().items():
            setattr(session, key, value)
        db.commit()
        db.refresh(session)
    return session

def delete_session(db: SessionLocal, session_id: str) -> bool:
    session = db.query(SessionDataModel).filter(SessionDataModel.session_id == session_id).first()
    if session:
        db.delete(session)
        db.commit()
        return True
    return False
