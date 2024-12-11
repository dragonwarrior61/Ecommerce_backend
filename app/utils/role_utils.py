ROLE_MAPPING = {
    -1: "UnAllowed",
    0: "Warehouse Staff",
    1: "Allowed",
    2: "Site Manager",
    3: "Customer Support",
    4: "Administrator",
    5: "Replacement Manager",
    6: "Shipment Manager"
}

def convert_role_to_string(role: int) -> str:
    return ROLE_MAPPING.get(role, "Unknown")