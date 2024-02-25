#!/usr/bin/env python3

import argparse
from bs4 import BeautifulSoup
import fcntl
import hashlib
import os
import os.path
import re
import requests
import subprocess
import sys
import time
import toml

########
## UTIL
########
debug_prompts = False
transcript = None
config = None

def write_to_transcript(output):
    global transcript
    sys.stdout.write(output)
    sys.stdout.flush()
    if transcript:
        transcript.write(output)
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
    
def get_url_text_and_cache(url, regexp):
    cachedir = "./.urlcache"
    if not os.path.isdir(cachedir):
        os.makedirs(cachedir)
    cachefile = cachedir + '/' + hashlib.sha256(url.encode()).hexdigest() + '.txt'
    if os.path.isfile(cachefile):
        with open(cachefile, 'r') as file:
            return file.read()
    else:
        webpage = requests.get(url)
        soup = BeautifulSoup(webpage.text, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        match = re.search(regexp, text)
        if match:
            result = match.group(1) 
            text = regexp.replace("(.*)", result)
            with open(cachefile,"w") as file:
                file.write(text)
            return text
        else:
            print(f"WARNING: Regexp {regexp} not matched in URL '{url}'")
    return ""


#############
## GPT STUFF
#############
def tell_gpt(prompt):
    global debug_prompts
    if debug_prompts:
        write_to_transcript(prompt)
    if not prompt[-1] == '>':
        write_to_transcript('\n')
    return

#################
## REWRITE LOGIC
#################
def init_rewrites(game_init_text):
    global config
    tell_gpt(config['init']['gpt_init'])
    for pair in config['init']['background_urls']:
        url = pair[0]
        regexp = pair[1]
        background_text = get_url_text_and_cache(url, regexp)
        background_init = config['init']['background_init']
        tell_gpt(background_init.replace('{{{background}}}', background_text))
    tell_gpt(config['style']['tone'])
    tell_gpt(config['style']['length'])
    tell_gpt(config['init']['startup'])
    tell_gpt(game_init_text)
    return

def rewrite_response(command, response):
    global config
    # clean up input/output
    input = False
    if response[-1] == '>': # remove input prompt, if there
        response = response[:-1] 
        input = True
    command = command.rstrip()
    response = response.rstrip()

    # detect errors
    error = False
    for prefix in config['errors']['prefixes']:
        if response.startswith(prefix):
            error = True
    
    # rewrite
    template = config['responses']['generic']
    prompt = template.replace('{{{command}}}',command).replace('{{{response}}}',response)
    tell_gpt(prompt)
    if error:
        tell_gpt(config['errors']['generic'])
    else:
        tell_gpt(config['responses']['suffix'])
    if input == True:
        write_to_transcript('>')
    return

########
## MAIN
########
def main(): 
    global transcript, config
    parser = argparse.ArgumentParser(description='Script for an LLM-enhanced Infocom experience.')
    
    # Parse arguments
    parser.add_argument('--config', '-c', type=str, default='./lampgpt.toml', help='Configuration file name (default lampgpt.toml)')
    parser.add_argument('--transcript', '-t', type=str, help='Name of transcript output file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Output original ZIL interpreter input/output')
    parser.add_argument('--debug', '-d', action='store_true', help='Output all LLM inputs and outputs')
    parser.add_argument('--delay', '-s', type=int, default=5, help='Delay (in milliseconds) to wait for ZIL interpreter output in each turn')
    parser.add_argument('--bocfel', '-x', type=str, default='./bocfel-2.1.2/bocfel', help='File name of bocfel ZIL interpreter')
    parser.add_argument('--bocfelargs', '-z', type=str, default='', help='Optional arguments for bocfel ZIL interpreter')
    parser.add_argument('ZILFILE')
    args = parser.parse_args()

    # Process arguments and config
    if args.debug:
        debug_prompts = True
    if args.transcript:
        transcript = open(args.transcript, 'w')
    try:
        with open(args.config, 'r') as config_file:
            config = toml.load(config_file)
    except:
        print('Invalid or missing ToML configuration file (default is ./lampgpt.toml)')
        return

    # Launch the ZIL interpreter and manage its input/output
    bocfel_launch = [args.bocfel] + args.bocfelargs.split() + [args.ZILFILE]
    process = subprocess.Popen(bocfel_launch, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    configure_non_blocking_reads(process.stdout)

    try:
        time.sleep((10*args.delay)/1000.0)
        output = non_blocking_read(process.stdout)
        init_rewrites(output)
        if args.verbose:
            write_to_transcript(f"# ORIGINAL START: {output}")

        while True:
            command = sys.stdin.readline()
            if not command:  # If EOF, break the loop
                break

            # Get a command and the original ZIL interpreter response
            process.stdin.write(command)
            process.stdin.flush()
            if args.verbose:
                write_to_transcript(f"# ORIGINAL COMMAND: {command}")
            time.sleep((1.0*args.delay)/1000.0)
            response = non_blocking_read(process.stdout)
            if args.verbose:
                write_to_transcript(f"# ORIGINAL RESPONSE: {response}")

            rewrite_response(command, response)

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