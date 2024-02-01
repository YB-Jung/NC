


def NRC_2_Str( code ):
    if code == 0x31:
        return "Request out of range"

    if code == 0x10:
        return "General reject"

    if code == 0x11:
        return "Service not supported"

    if code == 0x12:
        return "Sub-function not support"

    if code == 0x13:
        return "Incorrect message length Or invalid format"

    return "Error code 0x{:02x}".format( code )