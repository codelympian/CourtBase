"""Aggregate all v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import auth, clubs, health, players, states, stats

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(states.router)
api_router.include_router(clubs.router)
api_router.include_router(players.router)
api_router.include_router(stats.router)
