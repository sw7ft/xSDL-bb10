import socket
import struct

# X11 connection parameters
host = "192.168.2.8"  # XSDL display IP address
port = 6000             # X server port

try:
    # Step 1: Connect to the X server using TCP
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    print("Connected to X server.")

    # Step 2: Send an initial setup message to the X server
    # Byte order: 'B' (big-endian), protocol version 11.0
    setup_message = struct.pack("=BxHHHHH", ord('B'), 11, 0, 0, 0, 0)
    sock.send(setup_message)

    # Step 3: Receive the server response (small buffer)
    response = sock.recv(1024)  # Increase buffer size slightly

    # Step 4: Extract and print key information from the setup response

    # Extract byte order (first byte in the response)
    byte_order = struct.unpack_from("=B", response, 0)[0]
    if byte_order == 0x42:
        print("Byte order: Big-endian")
    elif byte_order == 0x6C:
        print("Byte order: Little-endian")
    else:
        print(f"Unknown byte order: {byte_order}")

    # Protocol version (2 bytes each for major and minor)
    protocol_major, protocol_minor = struct.unpack_from("=HH", response, 2)
    print(f"Protocol version: {protocol_major}.{protocol_minor}")

    # Number of screens (2 bytes at offset 16)
    num_screens = struct.unpack_from("=H", response, 16)[0]
    print(f"Number of screens: {num_screens}")

    # Extract root window ID (4 bytes at offset 24)
    root_window_id = struct.unpack_from("=L", response, 24)[0]
    print(f"Root window ID: {root_window_id}")

    # Extract screen dimensions (width and height, 2 bytes each, at offset 32 and 34)
    screen_width = struct.unpack_from("=H", response, 32)[0]
    screen_height = struct.unpack_from("=H", response, 34)[0]
    print(f"Screen size: {screen_width}x{screen_height}")

    # Close the socket connection
    sock.close()

except Exception as e:
    print(f"Failed to connect or gather information from X server: {e}")
