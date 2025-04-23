def apply_checks(*checks):
    for check in checks:
        if result := check():
            return result
