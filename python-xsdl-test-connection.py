import socket
import struct

host = "192.168.1.101"  # Replace with your X server's IP address
port = 6000

def send_request(sock, request):
    sock.send(request)
    response = sock.recv(4096)  # Receive a large buffer
    return response

def parse_extensions(data):
    if len(data) < 32:
        return []
    num_extensions = struct.unpack('!B', data[1:2])[0]
    print(f"Number of extensions reported: {num_extensions}")
    extensions = []
    offset = 32  # Start after the standard reply header
    while offset < len(data):
        name_length = data[offset]
        offset += 1
        if offset + name_length > len(data):
            break
        name = data[offset:offset+name_length].decode('ascii', errors='ignore').strip()
        if name:  # Only add non-empty names
            extensions.append(name)
        offset += name_length
        # Pad to multiple of 4 bytes
        offset = (offset + 3) & ~3
    return extensions

def parse_vendor_name(data):
    try:
        vendor_length = struct.unpack("!H", data[8:10])[0]
        vendor_name = data[32:32+vendor_length].decode('ascii', errors='ignore').strip()
        return vendor_name
    except Exception as e:
        print(f"Error parsing vendor name: {e}")
        return "Unable to parse vendor name"

def parse_screen_info(data):
    try:
        root_window = struct.unpack("!I", data[132:136])[0]
        width_in_pixels = struct.unpack("!H", data[136:138])[0]
        height_in_pixels = struct.unpack("!H", data[138:140])[0]
        width_in_mm = struct.unpack("!H", data[140:142])[0]
        height_in_mm = struct.unpack("!H", data[142:144])[0]
        root_depth = struct.unpack("!B", data[144:145])[0]
        return {
            "root_window": hex(root_window),
            "width_pixels": width_in_pixels,
            "height_pixels": height_in_pixels,
            "width_mm": width_in_mm,
            "height_mm": height_in_mm,
            "root_depth": root_depth
        }
    except Exception as e:
        print(f"Error parsing screen info: {e}")
        return "Unable to parse screen info"

def query_extension(sock, extension_name):
    name_bytes = extension_name.encode('ascii')
    pad_length = -len(name_bytes) & 3  # Calculate padding to make total length a multiple of 4
    request = struct.pack("!BBHI" + str(len(name_bytes)) + "s" + str(pad_length) + "x",
                          98, 0, 2 + (len(name_bytes) + pad_length) // 4, len(name_bytes),
                          name_bytes)
    response = send_request(sock, request)
    if len(response) >= 32:
        present, major_opcode, first_event, first_error = struct.unpack("!BBBB", response[8:12])
        return {
            "present": bool(present),
            "major_opcode": major_opcode if present else None,
            "first_event": first_event if present else None,
            "first_error": first_error if present else None
        }
    return None

def get_server_info(sock):
    request = struct.pack("!BBHI", 0, 0, 1, 0)  # QueryVersion request
    response = send_request(sock, request)
    print("Server info response:")
    print_hex_dump(response)
    if len(response) >= 32:
        major_version, minor_version = struct.unpack("!HH", response[8:12])
        return {
            "major_version": major_version,
            "minor_version": minor_version
        }
    return None

def print_hex_dump(data, prefix=''):
    for i in range(0, len(data), 16):
        hex_values = ' '.join(f'{b:02x}' for b in data[i:i+16])
        ascii_values = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[i:i+16])
        print(f"{prefix}{i:04x}: {hex_values:<48} {ascii_values}")

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    setup_message = struct.pack("!BxHHHHHI", ord('B'), 11, 0, 0, 0, 0, 0)
    sock.send(setup_message)
    handshake_response = sock.recv(4096)
    print(f"Handshake response size: {len(handshake_response)} bytes")
    print("Raw handshake response:")
    print_hex_dump(handshake_response)

    if handshake_response[0] != 1:
        print("Handshake failed")
        sock.close()
        exit(1)

    vendor_name = parse_vendor_name(handshake_response)
    print(f"Vendor name from handshake: {vendor_name}")

    screen_info = parse_screen_info(handshake_response)
    print(f"Screen info: {screen_info}")

    extension_request = struct.pack("!BBHI", 99, 0, 1, 0)  # ListExtensions request
    extension_response = send_request(sock, extension_request)
    print(f"Extension response size: {len(extension_response)} bytes")
    print("Raw extension response:")
    print_hex_dump(extension_response)

    extensions = parse_extensions(extension_response)
    print("Extensions:")
    for ext in extensions:
        print(f"- {ext}")

    for ext in ["GLX", "RENDER", "SHAPE"]:
        ext_info = query_extension(sock, ext)
        print(f"{ext} extension info: {ext_info}")

    server_info = get_server_info(sock)
    print(f"Server info: {server_info}")

    sock.close()

except Exception as e:
    print(f"Error: {e}")
