from config import settings


def has_staff_role(member) -> bool:
    """True if member has any role listed in STAFF_ROLE_IDS. Works for both
    a slash command's interaction.user and a prefix command's ctx.author."""

    roles = getattr(member, "roles", None)

    if not roles:
        return False

    member_role_ids = {role.id for role in roles}

    return any(role_id in member_role_ids for role_id in settings.STAFF_ROLE_IDS)