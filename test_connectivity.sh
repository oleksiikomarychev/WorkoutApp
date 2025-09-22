#!/bin/bash

echo "Testing connectivity from workouts-service to plans-service"
docker compose exec workouts-service curl -v http://plans-service:8000/health

echo "Testing DNS resolution in workouts-service"
docker compose exec workouts-service nslookup plans-service

echo "Inspecting Docker network"
docker network inspect workoutapp_default
