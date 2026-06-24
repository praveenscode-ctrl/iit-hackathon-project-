import shortuuid

def make_mentor_reg_id() -> str:
    return f"MENTOR-{shortuuid.uuid()[:8].upper()}"
