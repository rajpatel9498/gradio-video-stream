import struct
with open('/tmp/shared_memory/video_stream.meta', 'wb') as f:
    f.write(struct.pack('III', 432, 768, 1))
print("Wrote metadata to /tmp/shared_memory/video_stream.meta")