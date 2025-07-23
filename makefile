.PHONY: run migrate makemigrations superuser

run:
	python3 -m uvicorn app.main:app --reload

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

superuser:
	python manage.py createsuperuser

alembic:
	python -m alembic 
	alembic revision --autogenerate -m "update_models"
	alembic upgrade head