SAFE = "SAFE"
CONFIRM = "CONFIRM"
CRITICAL = "CRITICAL"

def classify(tool_name, destination_exists=False):
    if tool_name == "delete_item":
        return CRITICAL
    if tool_name in {"copy_item", "move_item", "rename_item"} and destination_exists:
        return CONFIRM
    return SAFE
