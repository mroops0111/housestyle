def build(candidate: str) -> str:
    """Build a proposal.

    Args:
        candidate: the thing
    """
    # clamp the size — the CI runner has a mmap limit
    # previously returned null, now throws
    # see JIRA-1234 filed on 2025-03-14
    # the outcome of one turn: the reply
    # uses a semicolon; which is forbidden
    # truncate the list and so on...
    return candidate
