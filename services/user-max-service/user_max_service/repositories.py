from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from .models import UserMax, UserMaxDailyAgg
from .services.true_1rm_service import calculate_true_1rm


class UserMaxRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_max_by_id(self, user_max_id: int, user_id: str) -> UserMax | None:
        return self.db.query(UserMax).filter(
            UserMax.id == user_max_id, 
            UserMax.user_id == user_id
        ).first()

    def get_user_maxes_by_user(
        self, 
        user_id: str, 
        exercise_id: int | None = None, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[UserMax]:
        query = self.db.query(UserMax).filter(UserMax.user_id == user_id)
        if exercise_id is not None:
            query = query.filter(UserMax.exercise_id == exercise_id)
        return query.offset(skip).limit(limit).all()

    def get_user_maxes_by_exercise(
        self, 
        user_id: str, 
        exercise_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> list[UserMax]:
        return (
            self.db.query(UserMax)
            .filter(UserMax.user_id == user_id, UserMax.exercise_id == exercise_id)
            .order_by(UserMax.date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_maxes_by_exercises(self, user_id: str, exercise_ids: list[int]) -> list[UserMax]:
        return self.db.query(UserMax).filter(
            UserMax.user_id == user_id, 
            UserMax.exercise_id.in_(exercise_ids)
        ).all()

    def get_user_maxes_by_ids(self, user_id: str, ids: list[int]) -> list[UserMax]:
        records = self.db.query(UserMax).filter(
            UserMax.user_id == user_id, 
            UserMax.id.in_(ids)
        ).all()
        
        by_id = {um.id: um for um in records}
        ordered = [by_id[id_] for id_ in ids if id_ in by_id]
        return ordered

    def find_existing_user_max(
        self, 
        user_id: str, 
        exercise_id: int, 
        rep_max: int, 
        dt: date
    ) -> UserMax | None:
        return (
            self.db.query(UserMax)
            .filter(
                UserMax.user_id == user_id,
                UserMax.exercise_id == exercise_id,
                UserMax.rep_max == rep_max,
                UserMax.date == dt,
            )
            .first()
        )

    def create_user_max(self, user_max_data: dict) -> UserMax:
        db_user_max = UserMax(**user_max_data)
        self.db.add(db_user_max)
        return db_user_max

    def update_user_max(self, user_max: UserMax, payload: dict) -> UserMax:
        allowed_fields = ["exercise_id", "max_weight", "rep_max", "true_1rm", "verified_1rm"]
        for k, v in payload.items():
            if k in allowed_fields:
                setattr(user_max, k, v)
        return user_max

    def delete_user_max(self, user_max: UserMax) -> None:
        self.db.delete(user_max)

    def get_user_maxes_for_analysis(self, user_id: str, days_back: int | None = None) -> list[UserMax]:
        query = self.db.query(UserMax).filter(UserMax.user_id == user_id)
        
        if days_back:
            cutoff_date = datetime.utcnow().date() - timedelta(days=days_back)
            query = query.filter(UserMax.date >= cutoff_date)
        
        return query.order_by(UserMax.date.desc()).all()

    def get_daily_agg_for_user(self, user_id: str) -> list[UserMaxDailyAgg]:
        return self.db.query(UserMaxDailyAgg).filter(UserMaxDailyAgg.user_id == user_id).all()

    def purge_user_data(self, user_id: str) -> None:
        self.db.query(UserMaxDailyAgg).filter(
            UserMaxDailyAgg.user_id == user_id
        ).delete(synchronize_session=False)
        self.db.query(UserMax).filter(
            UserMax.user_id == user_id
        ).delete(synchronize_session=False)

    def get_daily_agg_record(
        self, 
        user_id: str, 
        exercise_id: int, 
        dt: date
    ) -> UserMaxDailyAgg | None:
        return (
            self.db.query(UserMaxDailyAgg)
            .filter(
                UserMaxDailyAgg.user_id == user_id,
                UserMaxDailyAgg.exercise_id == exercise_id,
                UserMaxDailyAgg.date == dt,
            )
            .first()
        )

    def delete_daily_agg_record(
        self, 
        user_id: str, 
        exercise_id: int, 
        dt: date
    ) -> None:
        self.db.query(UserMaxDailyAgg).filter(
            UserMaxDailyAgg.user_id == user_id,
            UserMaxDailyAgg.exercise_id == exercise_id,
            UserMaxDailyAgg.date == dt,
        ).delete(synchronize_session=False)

    def recompute_daily_agg_batch(self, user_id: str, exercise_date_pairs: list[tuple]) -> None:
        from sqlalchemy import and_
        
        date_groups = {}
        for exercise_id, dt in exercise_date_pairs:
            date_groups.setdefault(dt, []).append(exercise_id)
        
        for dt, exercise_ids in date_groups.items():
            self.db.query(UserMaxDailyAgg).filter(
                and_(
                    UserMaxDailyAgg.user_id == user_id,
                    UserMaxDailyAgg.date == dt,
                    UserMaxDailyAgg.exercise_id.in_(exercise_ids)
                )
            ).delete(synchronize_session=False)
            
            all_rows = self.db.query(UserMax).filter(
                and_(
                    UserMax.user_id == user_id,
                    UserMax.date == dt,
                    UserMax.exercise_id.in_(exercise_ids)
                )
            ).all()
            
            rows_by_exercise = {}
            for um in all_rows:
                rows_by_exercise.setdefault(um.exercise_id, []).append(um)
            
            for exercise_id in exercise_ids:
                rows = rows_by_exercise.get(exercise_id, [])
                if rows:
                    sum_true_1rm = 0.0
                    cnt = 0
                    for um in rows:
                        val = um.verified_1rm if getattr(um, "verified_1rm", None) is not None else calculate_true_1rm(um)
                        try:
                            v = float(val)
                        except (TypeError, ValueError):
                            continue
                        sum_true_1rm += v
                        cnt += 1
                    
                    if cnt > 0:
                        agg = UserMaxDailyAgg(
                            user_id=user_id,
                            exercise_id=exercise_id,
                            date=dt,
                            sum_true_1rm=sum_true_1rm,
                            cnt=cnt,
                        )
                        self.db.add(agg)

    def find_existing_user_max_bulk(
        self, 
        user_id: str, 
        exercise_date_pairs: list[tuple]
    ) -> dict[tuple, UserMax]:
        if not exercise_date_pairs:
            return {}
        
        from sqlalchemy import and_, tuple_
        
        records = self.db.query(UserMax).filter(
            and_(
                UserMax.user_id == user_id,
                tuple_(UserMax.exercise_id, UserMax.date).in_(exercise_date_pairs)
            )
        ).all()
        
        result = {}
        for record in records:
            key = (record.exercise_id, record.rep_max, record.date)
            result[key] = record
        
        return result

    def bulk_create_user_maxes(self, user_max_data_list: list[dict]) -> list[UserMax]:
        if not user_max_data_list:
            return []
        
        from sqlalchemy.dialects.postgresql import insert
        
        stmt = insert(UserMax).returning(UserMax)
        result = self.db.execute(stmt, user_max_data_list)
        self.db.flush()
        return list(result.scalars().all())

    def bulk_update_user_maxes(self, user_maxes: list[UserMax]) -> None:
        if not user_maxes:
            return
        
        self.db.bulk_save_objects(user_maxes, update_fields=['max_weight', 'exercise_name', 'true_1rm', 'verified_1rm', 'source'])
        self.db.flush()

    def get_user_maxes_for_recompute(
        self, 
        user_id: str,
        exercise_id: int, 
        dt: date
    ) -> list[UserMax]:
        return (
            self.db.query(UserMax)
            .filter(
                UserMax.user_id == user_id,
                UserMax.exercise_id == exercise_id,
                UserMax.date == dt,
            )
            .all()
        )

    def create_or_update_daily_agg(self, user_id: str, exercise_id: int, dt: date, sum_true_1rm: float, cnt: int) -> None:
        from sqlalchemy.dialects.postgresql import insert
        
        stmt = insert(UserMaxDailyAgg).values(
            user_id=user_id,
            exercise_id=exercise_id,
            date=dt,
            sum_true_1rm=sum_true_1rm,
            cnt=cnt
        )
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'exercise_id', 'date'],
            set_=dict(sum_true_1rm=sum_true_1rm, cnt=cnt)
        )
        
        self.db.execute(stmt)
        self.db.flush()