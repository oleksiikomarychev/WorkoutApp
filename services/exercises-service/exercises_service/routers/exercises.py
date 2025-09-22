@router.get("/{exercise_id}/exists", response_model=schemas.ExerciseExistsResponse)
async def exercise_exists(exercise_id: int, db: AsyncSession = Depends(get_db)):
    """Check if exercise exists"""
    result = await db.execute(select(models.Exercise).filter(models.Exercise.id == exercise_id))
    exists = result.scalars().first() is not None
    return {"exists": exists}
