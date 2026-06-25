"""
Admin Role Management endpoints.

Only the Super Admin (configured via SUPER_ADMIN_EMAIL env variable) can call
these endpoints. They allow granting and revoking Google-email-based admin
access for other team members.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_admin_user_repo
from app.core.security import AdminPrincipal, admin_auth
from app.repositories.admin_user_repository import AdminUserRepository
from app.schemas.smarthome import AdminRoleGrantRequest, AdminRoleResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/roles", tags=["admin_rbac"])


def _require_super_admin(principal: AdminPrincipal) -> None:
    if not principal.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="super_admin_required",
        )


@router.get("", response_model=list[AdminRoleResponse])
async def list_admins(
    principal: AdminPrincipal = Depends(admin_auth),
    repo: AdminUserRepository = Depends(get_admin_user_repo),
) -> list[AdminRoleResponse]:
    """List all granted admin accounts (Super Admin only)."""
    _require_super_admin(principal)
    docs = await repo.list_all()
    return [
        AdminRoleResponse(
            id=str(d["_id"]),
            email=d["email"],
            role=d.get("role", "admin"),
            granted_by=d.get("granted_by", ""),
            created_at=d["created_at"],
        )
        for d in docs
    ]


@router.post("", response_model=AdminRoleResponse, status_code=status.HTTP_201_CREATED)
async def grant_admin(
    payload: AdminRoleGrantRequest,
    principal: AdminPrincipal = Depends(admin_auth),
    repo: AdminUserRepository = Depends(get_admin_user_repo),
) -> AdminRoleResponse:
    """Grant admin access to a Google account email (Super Admin only)."""
    _require_super_admin(principal)
    try:
        doc = await repo.grant_admin(
            email=payload.email,
            role="admin",
            granted_by=principal.subject,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    logger.info("admin_role_granted email=%s granted_by=%s", payload.email, principal.subject)
    return AdminRoleResponse(
        id=str(doc["_id"]),
        email=doc["email"],
        role=doc["role"],
        granted_by=doc["granted_by"],
        created_at=doc["created_at"],
    )


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_admin(
    email: str,
    principal: AdminPrincipal = Depends(admin_auth),
    repo: AdminUserRepository = Depends(get_admin_user_repo),
) -> None:
    """Revoke admin access from a Google account email (Super Admin only)."""
    _require_super_admin(principal)

    # Prevent Super Admin from revoking themselves
    if email.lower().strip() == principal.subject.lower().strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cannot_revoke_self",
        )

    deleted = await repo.revoke_admin(email)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="admin_not_found",
        )
    logger.info("admin_role_revoked email=%s revoked_by=%s", email, principal.subject)
