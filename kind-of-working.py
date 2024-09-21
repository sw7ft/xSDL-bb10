import socket
import struct
import time
import logging
import binascii
import select

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def connect_to_x_server(host, display):
    logger.info("Attempting to connect to XSDL server at %s:%d", host, 6000 + display)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, 6000 + display))
    logger.info("Connected successfully to XSDL server")
    return s

def send_protocol_setup(sock):
    logger.info("Preparing protocol setup data")
    auth_proto_name = ""
    auth_proto_data = ""
    
    data = struct.pack("!BBHHHHHHII",
        0x42,  # byte-order (big-endian)
        0,     # unused
        11,    # protocol-major-version
        0,     # protocol-minor-version
        len(auth_proto_name),  # length of authorization-protocol-name
        len(auth_proto_data),  # length of authorization-protocol-data
        0,     # unused
        0,     # unused
        0,     # unused
        0      # unused
    )
    data += auth_proto_name.encode('ascii') + auth_proto_data.encode('ascii')
    
    # Pad to multiple of 4 bytes
    pad_len = -len(data) % 4
    data += b'\0' * pad_len
    
    logger.debug("Protocol setup data: %s", binascii.hexlify(data))
    logger.debug("Protocol setup data length: %d bytes", len(data))
    
    logger.info("Sending protocol setup data")
    sock.sendall(data)
    
    logger.info("Waiting for server response")
    ready = select.select([sock], [], [], 5)  # 5 second timeout
    if ready[0]:
        response = sock.recv(8)
        if not response:
            logger.error("Server closed the connection")
            raise Exception("Server closed the connection")
        logger.debug("Received response (hex): %s", binascii.hexlify(response))
    else:
        logger.error("Timeout waiting for server response")
        raise Exception("Timeout waiting for server response")
    
    if len(response) < 8:
        logger.error("Incomplete response from XSDL server. Expected 8 bytes, got %d", len(response))
        raise Exception("Incomplete response from XSDL server")
    
    response_type = response[0]
    logger.info("Response type: %d", response_type)
    
    if response_type == 0:
        error_code = struct.unpack("!B", response[1:2])[0]
        logger.error("XSDL server returned error code: %d", error_code)
        error_sequence = struct.unpack("!H", response[2:4])[0]
        logger.error("Error sequence: %d", error_sequence)
        error_resource_id = struct.unpack("!I", response[4:8])[0]
        logger.error("Error resource ID: %d", error_resource_id)
        raise Exception("XSDL server returned error: %d" % error_code)
    elif response_type == 2:
        logger.info("Authentication required")
        # Handle authentication if needed
        raise Exception("Authentication required (not implemented)")
    elif response_type != 1:
        logger.error("Unexpected response type from XSDL server: %d", response_type)
        raise Exception("Unexpected response type from XSDL server")
    
    additional_data_length = struct.unpack("!I", response[4:8])[0]
    logger.info("Protocol setup successful. Additional data length: %d", additional_data_length)
    return additional_data_length

def create_window(sock, window_id, parent, x, y, width, height):
    logger.info("Creating window (ID: %d, Parent: %d, Position: (%d, %d), Size: %dx%d)", 
                window_id, parent, x, y, width, height)
    data = struct.pack("!BBHIIIHHHHI", 1, 0, 10, window_id, parent, x, y, width, height, 0, 0)
    logger.debug("Window creation data (hex): %s", binascii.hexlify(data))
    sock.sendall(data)

def map_window(sock, window_id):
    logger.info("Mapping window (ID: %d)", window_id)
    data = struct.pack("!BBH", 8, 0, 2)
    data += struct.pack("!I", window_id)
    logger.debug("Window mapping data (hex): %s", binascii.hexlify(data))
    sock.sendall(data)

def create_gc(sock, gc_id, window_id):
    logger.info("Creating Graphics Context (ID: %d, Window: %d)", gc_id, window_id)
    data = struct.pack("!BBHII", 55, 0, 4, gc_id, window_id)
    logger.debug("GC creation data (hex): %s", binascii.hexlify(data))
    sock.sendall(data)

def draw_rectangle(sock, window_id, gc, x, y, width, height):
    logger.info("Drawing rectangle (Window ID: %d, GC: %d, Position: (%d, %d), Size: %dx%d)", 
                window_id, gc, x, y, width, height)
    data = struct.pack("!BBHIIHHHH", 70, 0, 5, window_id, gc, x, y, width, height)
    logger.debug("Rectangle drawing data (hex): %s", binascii.hexlify(data))
    sock.sendall(data)

def main():
    host = "192.168.2.8"  # Your XSDL server IP
    display = 0

    sock = None
    try:
        sock = connect_to_x_server(host, display)

        additional_data_length = send_protocol_setup(sock)

        logger.info("Receiving setup data")
        ready = select.select([sock], [], [], 5)  # 5 second timeout
        if ready[0]:
            setup_data = sock.recv(additional_data_length * 4)
            if not setup_data:
                logger.error("Server closed the connection during setup data reception")
                raise Exception("Server closed the connection during setup data reception")
            logger.debug("Received setup data (hex): %s", binascii.hexlify(setup_data))
        else:
            logger.error("Timeout waiting for setup data")
            raise Exception("Timeout waiting for setup data")

        if len(setup_data) < 8:
            logger.error("Insufficient setup data received. Expected at least 8 bytes, got %d", len(setup_data))
            raise Exception("Insufficient setup data received")

        root_window_id = struct.unpack("!I", setup_data[4:8])[0]
        logger.info("Root window ID: %d", root_window_id)

        window_id = root_window_id + 1
        gc_id = window_id + 1

        create_window(sock, window_id, root_window_id, 100, 100, 300, 200)
        map_window(sock, window_id)
        create_gc(sock, gc_id, window_id)

        # Add a delay to allow the window to be created and mapped
        logger.info("Waiting for 1 second before drawing")
        time.sleep(1)

        draw_rectangle(sock, window_id, gc_id, 20, 20, 260, 160)

        logger.info("Waiting for 5 seconds before closing")
        time.sleep(5)

    except socket.error as e:
        logger.exception("Socket error occurred: %s", str(e))
    except struct.error as e:
        logger.exception("Struct packing/unpacking error: %s", str(e))
    except Exception as e:
        logger.exception("An unexpected error occurred: %s", str(e))
    finally:
        if sock:
            sock.close()
            logger.info("Connection closed")

if __name__ == "__main__":
    main()
