#!/usr/bin/env python3

import argparse
from bs4 import BeautifulSoup
import fcntl
import hashlib
from openai import OpenAI
import os
import os.path
import re
import requests
import subprocess
import sys
import textwrap
import time
import toml

########
## UTIL
########
debug_log = None
transcript = None
config = None

def write_to_debug_log(output):
    global debug_log
    if debug_log != None:
        debug_log.write(output)
        debug_log.flush()

def write_to_transcript(output, log_only=False):
    global transcript
    write_to_debug_log(output)
    if not log_only:
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
    cachefile = cachedir + '/' + hashlib.md5(url.encode()).hexdigest() + '.txt'
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
gpt_client = None
gpt_messages = []
gpt_message = ""
gpt_model = None
gpt_temp = None
def add_to_gpt_prompt(prompt):
    global debug_log, gpt_message
    write_to_debug_log(prompt)
    if not prompt[-1] == '>':
        gpt_message = gpt_message + '\n'
    gpt_message = gpt_message + prompt
    return

def get_gpt_response(message_type):
    global gpt_messages, gpt_message, gpt_model, gpt_temp
    message = {'role': message_type, 'content': gpt_message}
    gpt_messages.append(message)
    gpt_message = ""
    json = gpt_client.chat.completions.create(model=gpt_model, 
                                              messages=gpt_messages, 
                                              temperature=gpt_temp)
    response = json.choices[0].message.content
    message = {'role': 'assistant', 'content': response}
    gpt_messages.append(message)
    return response

#################
## REWRITE LOGIC
#################
def init_rewrites(game_init_text, style):
    global config
    add_to_gpt_prompt(config['init']['gpt_init'])
    for pair in config['init']['background_urls']:
        url = pair[0]
        regexp = pair[1]
        background_text = get_url_text_and_cache(url, regexp)
        background_init = config['init']['background_init']
        add_to_gpt_prompt(background_init.replace('{{{background}}}', background_text))
    add_to_gpt_prompt(config['style']['tone_'+style])
    add_to_gpt_prompt(config['style']['length'])
    add_to_gpt_prompt(config['init']['startup'])
    add_to_gpt_prompt(config['style']['formatting'])
    if game_init_text[-1] == '>': # remove input prompt, if there
        game_init_text = game_init_text[:-1] 
        game_init_text = game_init_text.rstrip()
    add_to_gpt_prompt(game_init_text)
    return get_gpt_response('system')

def rewrite_response(command, response, style):
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
    add_to_gpt_prompt(prompt)
    if error:
        add_to_gpt_prompt(config['errors']['generic'])
    else:
        add_to_gpt_prompt(config['style']['tone_'+style])
        add_to_gpt_prompt(config['style']['length'])
        add_to_gpt_prompt(config['style']['caveat'])
        add_to_gpt_prompt(config['style']['formatting'])
        add_to_gpt_prompt(config['responses']['suffix'])
    gpt_response = get_gpt_response('user')
    
    write_to_transcript(textwrap.fill(gpt_response, width=80))
    if input == True:
        write_to_transcript('\n\n>')
    return gpt_response

########
## MAIN
########
def main(): 
    global transcript, config, debug_log, gpt_client, gpt_model, gpt_temp
    parser = argparse.ArgumentParser(description='Script for an LLM-enhanced Infocom experience.')
    
    # Parse arguments
    parser.add_argument('--config', '-c', type=str, default='./lampgpt.toml', help='Configuration file name (default lampgpt.toml)')
    parser.add_argument('--transcript', '-t', type=str, help='Name of transcript output file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Output original ZIL interpreter input/output')
    parser.add_argument('--debug', '-d', action='store_true', help='Output all LLM inputs and outputs')
    parser.add_argument('--delay', '-s', type=int, default=5, help='Delay (in milliseconds) to wait for ZIL interpreter output in each turn')
    parser.add_argument('--bocfel', '-x', type=str, default='./bocfel-2.1.2/bocfel', help='File name of bocfel ZIL interpreter')
    parser.add_argument('--bocfelargs', '-z', type=str, default='', help='Optional arguments for bocfel ZIL interpreter')
    parser.add_argument('--gpt_temp', '-T', type=int, default=5, help='Temperature of LLM model (integer percent; default 5%)')
    parser.add_argument('--gpt_auth', '-A', type=str, default='****MISSING API KEY****', help='Authorization token for LLM')
    parser.add_argument('--llm', '-L', type=str, default='gpt-4-turbo-preview', help='LLM to use (default gpt-4)')
    parser.add_argument('--style', '-S', type=str, default='pratchett', help='Style: pratchett, gumshoe, ...')
    parser.add_argument('ZILFILE')
    args = parser.parse_args()

    # Process arguments and config
    if args.debug:
        debug_log = open('./debug.log', 'w')
    if args.transcript:
        transcript = open(args.transcript, 'w')
    try:
        with open(args.config, 'r') as config_file:
            config = toml.load(config_file)
    except:
        print('ERROR: Invalid or missing ToML configuration file (default is ./lampgpt.toml)')
        return
    if config['style'].get('tone_'+args.style) == None:
        print(f'ERROR: Unknown LLM rewriting style "{args.style}"')
        return

    # init our LLM
    gpt_model = args.llm
    gpt_temp = (1.0*args.gpt_temp)/100.0
    gpt_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", args.gpt_auth))

    # Launch the ZIL interpreter and manage its input/output
    bocfel_launch = [args.bocfel] + args.bocfelargs.split() + [args.ZILFILE]
    process = subprocess.Popen(bocfel_launch, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    configure_non_blocking_reads(process.stdout)

    try:
        time.sleep((10*args.delay)/1000.0)
        output = non_blocking_read(process.stdout)
        start = init_rewrites(output, args.style)
        if debug_log != None and args.verbose:
            write_to_transcript(f"# ORIGINAL START: {output}")
        write_to_transcript(textwrap.fill(start, width=80))
        write_to_transcript('\n\n>')

        while True:
            # get the user command
            command = sys.stdin.readline()
            if not command:  # If EOF, break the loop
                break

            # get the original ZIL interpreter response
            process.stdin.write(command)
            process.stdin.flush()
            if debug_log != None and args.verbose:
                write_to_transcript(f"# ORIGINAL COMMAND: {command}")
            time.sleep((1.0*args.delay)/1000.0)
            response = non_blocking_read(process.stdout)
            if debug_log != None and args.verbose:
                write_to_transcript(f"# ORIGINAL RESPONSE: {response}")

            # get the GPT version of the command and the GPT-modified response
            modified_command = command
            write_to_transcript(modified_command, log_only=True)
            rewrite_response(command, response, args.style)

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