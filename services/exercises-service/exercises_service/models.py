from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ExerciseList(Base, AsyncAttrs):
    __tablename__ = "exercise_list"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    muscle_group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    equipment: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_muscles: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    synergist_muscles: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    movement_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    region: Mapped[str | None] = mapped_column(String(32), nullable=True)
    root_exercise_id: Mapped[int | None] = mapped_column(
        ForeignKey("exercise_list.id", ondelete="SET NULL"), 
        nullable=True, 
        index=True
    )
    gif_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    __table_args__ = (
        Index("ix_exercise_list_name_gin", "name", postgresql_ops={"name": "gin_trgm_ops"}),
        Index("ix_muscle_group_btree", "muscle_group"),
        Index("ix_equipment_btree", "equipment"),
    )

    root_exercise: Mapped["ExerciseList"] = relationship(
        "ExerciseList",
        remote_side=[id],
        foreign_keys=[root_exercise_id],
        back_populates="variants",
    )
    
    variants: Mapped[list["ExerciseList"]] = relationship(
        "ExerciseList",
        foreign_keys=[root_exercise_id],
        back_populates="root_exercise",
    )

    def __repr__(self):
        return f"<ExerciseList(id={self.id}, name='{self.name}')>"
