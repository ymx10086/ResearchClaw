"""Environment variables management routes."""

from __future__ import annotations

import os
from typing import Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from researchclaw.envs import EnvStore

router = APIRouter()


class EnvVar(BaseModel):
    key: str = Field(..., description="Environment variable key")
    value: str = Field(..., description="Environment variable value")


_DEFAULT_PROFILE = "default"


def _load_default_vars() -> dict[str, str]:
    store = EnvStore()
    profile = store.get(_DEFAULT_PROFILE) or {
        "name": _DEFAULT_PROFILE,
        "vars": {},
    }
    return dict(profile.get("vars", {}))


def _save_default_vars(vars_map: dict[str, str]) -> None:
    store = EnvStore()
    store.save({"name": _DEFAULT_PROFILE, "vars": vars_map})


@router.get("", response_model=List[EnvVar])
async def list_envs() -> List[EnvVar]:
    envs = _load_default_vars()
    return [EnvVar(key=k, value=v) for k, v in sorted(envs.items())]


@router.put("", response_model=List[EnvVar])
async def put_envs(body: Dict[str, str]) -> List[EnvVar]:
    cleaned = {}
    for key, value in body.items():
        if not key.strip():
            raise HTTPException(
                status_code=400,
                detail="Env key cannot be empty",
            )
        cleaned[key.strip()] = value

    _save_default_vars(cleaned)

    for key, value in cleaned.items():
        os.environ[key] = value

    return [EnvVar(key=k, value=v) for k, v in sorted(cleaned.items())]


@router.delete("/{key}", response_model=List[EnvVar])
async def delete_env(key: str) -> List[EnvVar]:
    envs = _load_default_vars()
    if key not in envs:
        raise HTTPException(
            status_code=404,
            detail=f"Env var '{key}' not found",
        )

    envs.pop(key)
    _save_default_vars(envs)
    os.environ.pop(key, None)

    return [EnvVar(key=k, value=v) for k, v in sorted(envs.items())]
