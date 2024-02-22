#!/usr/bin/env python3

import fcntl
import os
import subprocess
import sys
import time

def configure_non_blocking_reads(stream):
    fd = stream.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

def non_blocking_read(stream):
    try:
        return stream.read()
    except:
        return ""

def main(): 
    if len(sys.argv) < 2:
        print("Usage: python3 lampgpt.py path-to-zil-file")
        sys.exit(1)

    # Use the first argument as the zip file
    zilfile = sys.argv[1]

    # Prepare the subprocess to launch the binary and manage its input/output
    process = subprocess.Popen(['./bocfel', zilfile], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    configure_non_blocking_reads(process.stdout)

    try:
        while True:
            time.sleep(0.005)

            # Process the output from the subprocess
            output = non_blocking_read(process.stdout)
            modified_output = output.replace("mailbox", "snowman")
            sys.stdout.write(modified_output)
            sys.stdout.flush()

            # Read a single line from stdin
            line = sys.stdin.readline()
            if not line:  # If EOF, break the loop
                break
            modified_line = line.replace("house", "horse")

            # Write the modified input to the subprocess
            process.stdin.write(modified_line)
            process.stdin.flush()

    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting.")
    finally:
        # Cleanup
        process.stdin.close()
        process.terminate()
        process.wait()

    # Check for errors
    if process.returncode != 0 and process.returncode != -15:  # -15 is SIGTERM
        # Read any errors from stderr
        errors = process.stderr.read()
        print(f"Error running ZIL interpreter: {errors}", file=sys.stderr)

if __name__ == "__main__":
    main()