#!/usr/bin/env python3

from anthropic import Anthropic
import argparse
from bs4 import BeautifulSoup
from dotenv import load_dotenv
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
import vertexai
from vertexai.generative_models import GenerativeModel

###########
## GLOBALS
###########
class GlobalState:
    def __init__(self):
        self.args = None        # script args
        self.debug_log = None   # open fd for a debug log file
        self.transcript = None  # open fd for a transcript file
        self.config = None      # the lampgpt ToML config
        self.game = None        # the game ToML config
        self.game_chatlog = []  # the log of game inputs and outputs
        self.llm = None         # the config of the LLM to be used
        self.llm_client = None  # the LLM client reference
        self.llm_chatlog = []   # the log of LLM inputs and outputs
        self.llm_prompt = ""    # the current LLM prompt being constructed
        self.seenrooms = set([])# title descriptions of all rooms visited
state = GlobalState()

########
## UTIL
########
def write_to_debug_log(output):
    global state
    if state.debug_log != None:
        state.debug_log.write(output)
        state.debug_log.flush()

def write_to_transcript(output, log_only=False):
    global state
    write_to_debug_log(output)
    if not log_only:
        sys.stdout.write(output)
        sys.stdout.flush()
    if state.transcript:
        state.transcript.write(output)
        state.transcript.flush()

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
        text = soup.get_text(separator='\n', strip=True)
        match = re.search(regexp, text, re.DOTALL)
        if match:
            result = match.group(1) 
            text = regexp.replace("(.*)", result)
            with open(cachefile,"w") as file:
                file.write(text)
            return text
        else:
            print(f"WARNING: Regexp {regexp} not matched in URL '{url}'")
    return ""

def get_file_text(filename, regexp):
    if os.path.isfile(filename):
        with open(filename, 'r') as file:
            text = file.read()
        match = re.search(regexp, text, re.DOTALL)
        if match:
            result = match.group(1) 
            return regexp.replace("(.*)", result)
        else:
            print(f"WARNING: Regexp {regexp} not matched in file '{filename}'")
    else:
        print(f"WARNING: File {filename} not found as background info.")
    return ""

##############
## GAME STUFF
##############
def get_room_desc(text):
    global state
    text = text.lstrip()
    for room in state.game['syntax']['rooms']:
        if text.startswith(room):
            return room
    return None

def process_rewritten_response_of_room(original, rewritten):
    room = get_room_desc(original)
    if room == None:
        return rewritten
    if room not in state.seenrooms: # update seenrooms
        state.seenrooms.add(room)
    text = rewritten.lstrip()
    if text.lower().startswith(room.lower()):
        text = text[len(room):].lstrip()
    text = room + ':\n' + text
    return text

def add_to_game_log(output, command=False):
    global state
    if state.debug_log != None and state.args.verbose:
        write_to_transcript(f"# ORIGINAL GAME: {output}")
    if command:
        output = f"{state.config['responses']['command_prefix']} {output}"
    if output.rstrip()[-1] == '>': # remove input prompt, if there
        output = output.rstrip()[:-1] 
        output = output.rstrip() + '\n'
    state.game_chatlog.append([command, output])

def get_rooms_and_gamelog():
    global state
    gamelog_count = state.config['init']['gamelog_count']
    if gamelog_count == 0:
        gamelog_count = len(state.game_chatlog)
    else:
        gamelog_count = 2*gamelog_count
    gamelog = state.game_chatlog[-gamelog_count:]
    gamelog_text = '\n'.join([text for [b,text] in gamelog])

    also_visited_rooms = state.seenrooms.copy()
    for response in [text for [b,text] in gamelog if b == False]:
        room = get_room_desc(response)
        if not room == None and room in also_visited_rooms:
            also_visited_rooms.remove(room)
    rooms_text = ', '.join([f"'{room}'" for room in also_visited_rooms])
    return [rooms_text,gamelog_text]

#############
## GPT STUFF
#############
def add_to_llm_prompt(prompt):
    global state
    write_to_debug_log(prompt)
    if not prompt[-1] == '>':
        state.llm_prompt = state.llm_prompt + '\n'
    state.llm_prompt = state.llm_prompt + prompt
    return

def get_llm_response(message_type):
    global state

    prompt = {'role': message_type, 'content': state.llm_prompt}
    state.llm_chatlog.append(prompt)

    # make a request with the prompt
    if state.llm['config']['api'] == 'openai':
        resp = state.llm_client.chat.completions.create(model=state.llm['config']['name'], 
                                                        messages=[ prompt ], 
                                                        temperature=state.llm['config']['temp'])
        tokens = resp.usage.prompt_tokens
        response = resp.choices[0].message.content
    elif state.llm['config']['api'] == 'anthropic':
        prompt['role'] = 'user'
        resp = state.llm_client.messages.create(model=state.llm['config']['name'], 
                                                max_tokens=state.llm['config']['max_tokens'],
                                                messages=[ prompt ], 
                                                temperature=state.llm['config']['temp'])
        tokens = resp.usage.input_tokens
        response = resp.content[0].text
    elif state.llm['config']['api'] == 'google':
        response = state.llm_client.send_message(state.llm_prompt)
        tokens = response.to_dict()['usage_metadata']['prompt_token_count']
        response = response.text
    elif state.llm['config']['api'] == 'debug':
        print(state.llm_prompt)
        response = ""
        tokens = 0
    write_to_debug_log(f"# DEBUG: Prompt token count is {tokens}\n")


    message = {'role': 'assistant', 'content': response}
    state.llm_chatlog.append(message)

    # reset the prompt
    state.llm_prompt = ""
    return response

#################
## REWRITE LOGIC
#################
def init_rewrites(game_init_text, style):
    global state
    add_to_llm_prompt(state.config['init']['llm_init'])

    if state.args.bginfo:
        background_init = state.config['init']['background_init']
        add_to_llm_prompt(background_init.replace('{{{background}}}', state.game['game']['setup']))
        for pair in state.game['game']['background_urls']:
            url = pair[0]
            regexp = pair[1]
            background_text = get_url_text_and_cache(url, regexp).strip()
            if background_text != '':
                add_to_llm_prompt(background_init.replace('{{{background}}}', background_text))
        for pair in state.game['game']['background_files']:
            filename = pair[0]
            regexp = pair[1]
            background_text = get_file_text(filename, regexp).strip()
            if background_text != '':
                add_to_llm_prompt(background_init.replace('{{{background}}}', background_text))

    add_to_llm_prompt(state.config['style']['tone_'+style])
    add_to_llm_prompt(state.config['style']['length'])
    add_to_llm_prompt(state.config['style']['formatting'])
    add_to_llm_prompt(state.config['init']['startup'])

    if game_init_text[-1] == '>': # remove input prompt, if there
        game_init_text = game_init_text[:-1] 
        game_init_text = game_init_text.rstrip()
    add_to_llm_prompt(game_init_text)
    return get_llm_response('system')

def rewrite_response(command, response, style):
    global state
    # clean up input/output
    input = False
    if response[-1] == '>': # remove input prompt, if there
        response = response[:-1] 
        input = True
    command = command.rstrip()
    response = response.rstrip()

    # instructions
    if state.args.repeat:
        add_to_llm_prompt(state.config['init']['llm_init'])
        add_to_llm_prompt(state.config['style']['tone_'+style])
        add_to_llm_prompt(state.config['style']['length'])
        add_to_llm_prompt(state.config['style']['formatting'])
        add_to_llm_prompt(state.config['style']['caveat'])
        add_to_llm_prompt(state.config['init']['gamelog_init'])

        [visited_rooms, gamelog] = get_rooms_and_gamelog()
        template = state.config['init']['gamelog_init']
        template = template.replace('{{{visited_rooms}}}',visited_rooms)
        template = template.replace('{{{gamelog}}}',gamelog)
        add_to_llm_prompt(template)
    
    # detect and try to fix errors
    error = False
    for prefix in state.config['errors']['prefixes']:
        if response.startswith(prefix):
            error = True
    if error:
        add_to_llm_prompt(state.config['errors']['generic'])

    # rewrite
    template = state.config['responses']['generic']
    prompt = template.replace('{{{command}}}',command).replace('{{{response}}}',response)
    add_to_llm_prompt(prompt)
    add_to_llm_prompt(state.config['responses']['suffix'])
    llm_response = get_llm_response('user')
    llm_response = process_rewritten_response_of_room(response, llm_response)

    write_to_transcript(textwrap.fill(llm_response, width=80, replace_whitespace=True, break_long_words=False))
    if input == True:
        write_to_transcript('\n\n>')
    return llm_response

########
## MAIN
########
def main(): 
    global state
    parser = argparse.ArgumentParser(description='Script for an LLM-enhanced Infocom experience.')
    
    # Parse arguments
    parser.add_argument('--config', '-c', type=str, default='./lampgpt.toml', help='Configuration file name (default lampgpt.toml)')
    parser.add_argument('--transcript', '-t', type=str, help='Name of transcript output file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Output original ZIL interpreter input/output')
    parser.add_argument('--debug', '-d', action='store_true', help='Output all LLM inputs and outputs')
    parser.add_argument('--delay', '-s', type=int, default=5, help='Wait (in milliseconds) for interpreter output in each turn')
    parser.add_argument('--bocfel', '-x', type=str, default='./bocfel-2.1.2/bocfel', help='File name of bocfel ZIL interpreter')
    parser.add_argument('--bocfelargs', '-z', type=str, default='', help='Optional arguments for bocfel ZIL interpreter')
    parser.add_argument('--llm_temp', '-T', type=int, help='Temperature of LLM model (integer percent; default 5%%)')
    parser.add_argument('--llm_auth', '-A', type=str, help='Authorization token for LLM')
    parser.add_argument('--llm', '-L', type=str, default='chatgpt4', help='LLM to use (debug, gemini, chatgpt4, claude)')
    parser.add_argument('--style', '-S', type=str, default='original', help='Style: pratchett, gumshoe, ...')
    parser.add_argument('--bginfo', '-B', action='store_true', help='Add extra background info to the LLM prompts')
    parser.add_argument('--repeat', '-R', action='store_true', help='Repeat instructions at each prompt')
    parser.add_argument('GAMENAME')
    args = parser.parse_args()

    # Process arguments and config
    load_dotenv()
    state.args = args
    if args.debug:
        state.debug_log = open('./debug.log', 'w')
    if args.transcript:
        state.transcript = open(args.transcript, 'w')
    try:
        with open(args.config, 'r') as config_file:
            config = toml.load(config_file)
            state.config = config
    except:
        print('ERROR: Invalid or missing ToML configuration file (default is ./lampgpt.toml)')
        return
    try:
        gamepath = args.GAMENAME + '.toml'
        if not os.path.isfile(gamepath):
            gamepath = './infocom/' + gamepath
        with open(gamepath, 'r') as game_file:
            game = toml.load(game_file)
            state.game = game
    except:
        print(f'ERROR: Invalid or missing {gamepath} ToML game config file')
        return
    try:
        if args.llm == 'debug':
            state.llm = {}
            state.llm['config'] = {}
            state.llm['config']['api'] = 'debug'
        else:
            with open(args.llm + '.toml', 'r') as llm_config:
                llm = toml.load(llm_config)
                state.llm = llm
            if args.llm_temp != None:
                state.llm['config']['temp'] = (1.0*args.llm_temp)/100.0
            if args.llm_auth != None:
                state.llm['config']['auth'] = args.llm_auth
    except:
        print(f'ERROR: Invalid or missing {args.llm} ToML LLM config file')
        return
    if config['style'].get('tone_'+args.style) == None:
        print(f'ERROR: Unknown LLM rewriting style "{args.style}"')
        return

    # create the LLM client
    if state.llm['config']['api'] == 'openai':
        state.args.repeat = True
        if state.llm['config'].get('auth') == None: # allow command line to override env var
            state.llm['config']['auth'] = os.environ.get("OPENAI_API_KEY", "***MISSING API KEY***")
        state.llm_client = OpenAI(api_key=state.llm['config']['auth'])
    elif state.llm['config']['api'] == 'anthropic':
        state.args.repeat = True
        if state.llm['config'].get('auth') == None: # allow command line to override env var
            state.llm['config']['auth'] = os.environ.get("ANTHROPIC_API_KEY", "***MISSING API KEY***")
        state.llm_client = Anthropic(api_key=state.llm['config']['auth'])
    elif state.llm['config']['api'] == 'google':
        state.args.repeat = False
        vertexai.init(project=state.llm['config']['project'], location=state.llm['config']['location'])
        model = GenerativeModel(state.llm['config']['name'])
        state.llm_client = model.start_chat(response_validation=False)
    else:
        state.llm['config']['api'] = 'debug' # redundant; included for clarity

    # Launch the ZIL interpreter and manage its input/output
    bocfel_launch = [args.bocfel] + args.bocfelargs.split() + [game['game']['path'].replace(' ','\\ ')]
    process = subprocess.Popen(bocfel_launch, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    configure_non_blocking_reads(process.stdout)

    try:
        time.sleep((10*args.delay)/1000.0)
        output = non_blocking_read(process.stdout)
        add_to_game_log(f"{output}\n", command=False)
        start = init_rewrites(output, args.style)
        write_to_transcript(textwrap.fill(start, width=80, replace_whitespace=False, break_long_words=False, drop_whitespace=False))
        write_to_transcript('\n\n>')

        while True:
            # get the user command
            command = sys.stdin.readline()
            if not command:  # If EOF, break the loop
                break

            # get the original ZIL interpreter response
            process.stdin.write(command)
            process.stdin.flush()
            time.sleep((1.0*args.delay)/1000.0)
            response = non_blocking_read(process.stdout)

            # get the LLM version of the command and the LLM-modified response
            modified_command = command # TODO rewrite the command
            write_to_transcript(modified_command, log_only=True)
            rewrite_response(command, response, args.style)

            add_to_game_log(command, command=True)
            add_to_game_log(response, command=False)

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