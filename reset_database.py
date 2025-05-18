import datetime
import os
import random
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.workout_models import (Workout, Exercise, UserMax, ExerciseList, EffortType, Progressions, ProgressionTemplate)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def generate_mock_exercises():
    prompt = """
    Generate a list of 10 diverse strength training exercises as a valid JSON array. 
    Each exercise must have these exact keys:
    {
        "name": "Exercise Name",
        "description": "Brief exercise description",
        "muscle_group": "Primary Muscle Group",
        "equipment": "Required Equipment"
    }
    Respond ONLY with a valid JSON array. Do not include any additional text.
    """
    
    try:
        response = model.generate_content(prompt)
        
        text = response.text.strip()
        
        import re
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            text = json_match.group(0)
        
        import json
        exercises_data = json.loads(text)
        
        return [
            ExerciseList(
                name=exercise['name'], 
                description=exercise['description'], 
                muscle_group=exercise['muscle_group'],
                equipment=exercise['equipment']
            ) for exercise in exercises_data
        ]
    except Exception as e:
        print(f"Error generating exercises: {e}")
        return [
            ExerciseList(
                name='Bench Press', 
                description='Compound chest exercise', 
                muscle_group='Chest',
                equipment='Barbell'
            ),
            ExerciseList(
                name='Squats', 
                description='Lower body compound movement', 
                muscle_group='Legs',
                equipment='Barbell'
            ),
            ExerciseList(
                name='Deadlift', 
                description='Full body strength exercise', 
                muscle_group='Back',
                equipment='Barbell'
            )
        ]

def generate_mock_user_maxes(exercises):
    return [
        UserMax(
            exercise=exercise,
            max_weight=random.randint(50, 150),
            rep_max=random.randint(3, 8)
        ) for exercise in exercises
    ]

def generate_mock_progressions(user_maxes):
    return [
        Progressions(
            user_max=user_max,
            sets=random.randint(3, 5),
            intensity=random.uniform(1, 10),
            effort=random.uniform(1, 10),
            volume=random.randint(10, 30)        
            )
            for user_max in user_maxes
    ]

def generate_mock_progression_templates(progressions):
    return [
        ProgressionTemplate(
            name=f"Progression for {progression.user_max.exercise.name}",
            user_max=progression.user_max,
            sets=progression.sets,
            intensity=progression.intensity,
            volume=progression.volume,
            effort=progression.effort
        ) for progression in progressions
    ]

def generate_mock_exercises_for_workouts(workouts, exercise_list):
    exercises = []
    for workout in workouts:
        workout_exercises = random.sample(exercise_list, min(3, len(exercise_list)))
        for exercise in workout_exercises:
            exercises.append(
                Exercise(
                    name=exercise.name,
                    sets=random.randint(3, 5),
                    reps=random.randint(5, 12),
                    weight=random.randint(50, 150),
                    workout=workout
                )
            )
    return exercises

def reset_database():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)

    exercise_list = generate_mock_exercises()
    session.add_all(exercise_list)

    workouts = [
        Workout(
            name='Upper Body Day', 
            description='Focusing on chest and arms with RPE tracking'
        ),
        Workout(
            name='Lower Body Day', 
            description='Leg day with heavy squats using RIR method'
        )
    ]
    session.add_all(workouts)

    user_maxes = generate_mock_user_maxes(exercise_list)
    session.add_all(user_maxes)

    progressions = generate_mock_progressions(user_maxes)
    session.add_all(progressions)

    progression_templates = generate_mock_progression_templates(progressions)
    session.add_all(progression_templates)

    exercises = generate_mock_exercises_for_workouts(workouts, exercise_list)
    session.add_all(exercises)

    session.commit()
    session.close()

if __name__ == "__main__":
    reset_database()
