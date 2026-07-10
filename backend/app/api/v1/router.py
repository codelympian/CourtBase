"""Aggregate all v1 routers."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    auth,
    categories,
    clubs,
    events,
    health,
    matches,
    players,
    ranking_rules,
    rankings,
    registrations,
    states,
    stats,
    tournaments,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(states.router)
api_router.include_router(clubs.router)
api_router.include_router(players.router)
api_router.include_router(stats.router)
api_router.include_router(categories.router)
api_router.include_router(tournaments.router)
api_router.include_router(events.router)
api_router.include_router(registrations.router)
api_router.include_router(matches.router)
api_router.include_router(ranking_rules.router)
api_router.include_router(rankings.router)
