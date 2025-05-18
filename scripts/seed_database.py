from faker import Faker
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app import user_models, workout_models
from app.user_models import UserRole
import random
from datetime import datetime, timedelta

fake = Faker()

def create_users(db: Session, num_users: int = 10):
    users = []
    for _ in range(num_users):
        role = random.choice(list(UserRole))
        user = user_models.User(
            email=fake.unique.email(),
            hashed_password=fake.password(),  # В реальном приложении используйте хеширование
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            role=role
        )
        db.add(user)
        users.append(user)
    
    db.commit()
    return users

def create_athletes(db: Session, users: list):
    athletes = []
    for user in users:
        if user.role == UserRole.ATHLETE:
            athlete = user_models.Athlete(
                user_id=user.id,
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=65)
            )
            db.add(athlete)
            athletes.append(athlete)
    
    db.commit()
    return athletes

def create_trainers(db: Session, users: list):
    trainers = []
    for user in users:
        if user.role == UserRole.TRAINER:
            trainer = user_models.Trainer(
                user_id=user.id,
                specialization=random.choice(['Strength', 'Cardio', 'Yoga', 'Crossfit', 'Bodybuilding'])
            )
            db.add(trainer)
            trainers.append(trainer)
    
    db.commit()
    return trainers

def create_workouts(db: Session, num_workouts: int = 50):
    workouts = []
    for _ in range(num_workouts):
        workout = workout_models.Workout(
            name=fake.catch_phrase(),
            description=fake.text(max_nb_chars=200) if random.random() > 0.5 else None
        )
        db.add(workout)
        workouts.append(workout)
    
    db.commit()
    return workouts

def create_exercises(db: Session, workouts: list, num_exercises: int = 100):
    exercise_list = db.query(workout_models.ExerciseList).all()
    exercises = []
    for _ in range(num_exercises):
        workout = random.choice(workouts)
        exercise_template = random.choice(exercise_list)
        exercise = workout_models.Exercise(
            name=exercise_template.name,
            sets=random.randint(3, 5),
            reps=random.randint(8, 15),
            weight=random.uniform(10, 100),
            workout_id=workout.id
        )
        db.add(exercise)
        exercises.append(exercise)
    
    db.commit()
    return exercises

def create_exercise_list(db: Session):
    exercise_templates = [
        {"name": "Bench Press", "muscle_group": "Chest", "equipment": "Barbell"},
        {"name": "Squats", "muscle_group": "Legs", "equipment": "Barbell"},
        {"name": "Deadlift", "muscle_group": "Back", "equipment": "Barbell"},
        {"name": "Pull-ups", "muscle_group": "Back", "equipment": "Bodyweight"},
        {"name": "Push-ups", "muscle_group": "Chest", "equipment": "Bodyweight"},
        {"name": "Overhead Press", "muscle_group": "Shoulders", "equipment": "Barbell"},
        {"name": "Rows", "muscle_group": "Back", "equipment": "Barbell"}
    ]

    existing_exercises = db.query(workout_models.ExerciseList).count()
    if existing_exercises == 0:
        for ex in exercise_templates:
            exercise = workout_models.ExerciseList(**ex)
            db.add(exercise)
        db.commit()

def seed_database():
    # Создаем все таблицы
    user_models.Base.metadata.create_all(bind=engine)
    workout_models.Base.metadata.create_all(bind=engine)

    # Создаем сессию
    db = SessionLocal()

    try:
        # Создаем список упражнений
        create_exercise_list(db)

        # Заполняем базу данными
        users = create_users(db)
        athletes = create_athletes(db, users)
        trainers = create_trainers(db, users)
        workouts = create_workouts(db)
        exercises = create_exercises(db, workouts)

        print(f"Создано: {len(users)} пользователей, {len(athletes)} атлетов, {len(trainers)} тренеров, {len(workouts)} тренировок, {len(exercises)} упражнений")

    except Exception as e:
        print(f"Ошибка при заполнении базы данных: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
