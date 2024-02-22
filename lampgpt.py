#!/usr/bin/env python3

import argparse
import fcntl
import os
import subprocess
import sys
import time

transcript = None

def write_to_transcript(output):
    global transcript
    modified_output = output.replace("mailbox", "snowman")
    sys.stdout.write(modified_output)
    sys.stdout.flush()
    if transcript:
        transcript.write(modified_output)
        transcript.flush()

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
    global transcript
    parser = argparse.ArgumentParser(description='Script for an LLM-enhanced Infocom experience.')
    
    # Parse arguments
    parser.add_argument('--config', '-c', type=str, default='./lampgpt.toml', help='Configuration file name (default lampgpt.toml)')
    parser.add_argument('--transcript', '-t', type=str, help='Name of transcript output file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Increase output verbosity')
    parser.add_argument('--delay', '-d', type=int, default=5, help='Delay (in milliseconds) to wait for ZIL interpreter output in each turn')
    parser.add_argument('--bocfel', '-x', type=str, default='./bocfel-2.1.2/bocfel', help='Executable file name for bocfel ZIL runtime')
    parser.add_argument('ZILFILE')
    args = parser.parse_args()

    # Process arguments and config
    if args.transcript:
        transcript = open(args.transcript, 'w')

    # Launch the ZIL interpreter and manage its input/output
    process = subprocess.Popen([args.bocfel, args.ZILFILE], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    configure_non_blocking_reads(process.stdout)

    try:
        while True:
            time.sleep((1.0*args.delay)/1000.0)

            # Process the output from the subprocess
            output = non_blocking_read(process.stdout)
            write_to_transcript(output)

            # Read a single line from stdin
            line = sys.stdin.readline()
            if not line:  # If EOF, break the loop
                break
            modified_line = line.replace("house", "horse")

            # Write the modified input to the subprocess
            process.stdin.write(modified_line)
            process.stdin.flush()
            write_to_transcript(modified_line)
            if args.verbose:
                print(f"# ORIGINAL INPUT: {line}")

    except KeyboardInterrupt:
        print("\nScript interrupted by user. Exiting.")
    finally:
        # Cleanup
        process.stdin.close()
        process.terminate()
        process.wait()
    # Check for errors before exiting
    if process.returncode != 0 and process.returncode != -15:  # -15 is SIGTERM
        errors = process.stderr.read()
        if errors != "":
            print(f"\nError running ZIL interpreter: {errors}", file=sys.stderr)

if __name__ == "__main__":
    main()