def get_user_owner(user):
    """
    Resolve the owner for the given user.
    - If user is Super Admin, return None (they see all).
    - If user is Owner, return user.
    - If user is Employee, return user.parent.
    """
    if not user or not user.is_authenticated:
        return None
        
    if getattr(user, 'is_super_admin', False):
        return None
        
    # If user has a parent, they are an employee; parent is the owner
    if getattr(user, 'parent', None):
        return user.parent
        
    # Otherwise, they are the owner
    return user
