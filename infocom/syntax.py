#!/usr/bin/env python3
import sys
import re

debug = None

def process_pattern(filenames, type, pattern, output_dict, process_func):
    # Iterate over the filenames provided in the command line
    for filename in filenames:
        # Open and read the file
        try:
            with open(filename, 'r') as file:
                text = file.read()
            matches = re.findall(pattern, text)
            if debug and len(matches) > 0:
                print(f"{filename}\tCNT({type}) = {len(matches)}")
            for match in matches:
                process_func(output_dict, match)
        except FileNotFoundError:
            print(f"File {filename} not found. Skipping.")

def isgood(word):
    if '#' in word or '\\' in word or '$' in word or '\t' in word:
        return False
    return True

#
# Return a map of verbs to sets of verb synonyms
#
def find_syntax_verbs(filenames):
    def process_verb_synonym(dict, match):
        syns = match.split()
        verb = syns[0].lower()
        if isgood(verb):
            syns = [syn.lower() for syn in syns if isgood(syn)]
            for i, item in enumerate(syns):
                if item[:1] == ';':
                    syns = syns[:i]
                    break
            if not dict.get(verb):
                dict[verb] = set([])
            dict[verb] = dict[verb].union(set(syns))
    verbs = {}
    verb_syns_pattern = re.compile(r'^<(?:VERB-)?SYNONYM ([^<>]+?)>', flags=re.DOTALL|re.MULTILINE)
    process_pattern(filenames, "verb_synonym", verb_syns_pattern, verbs, process_verb_synonym)
    synonyms = verbs.copy()

    def process_verb(dict, match):
        verb = match.lower()
        if isgood(verb) and dict.get(verb) == None:
            dict[verb] = set([verb])
    verb_pattern = re.compile(r'^<SYNTAX ([^<>\s]+?)\s[^=]*=[^<>]*?>', flags=re.DOTALL|re.MULTILINE)
    process_pattern(filenames, "verb", verb_pattern, verbs, process_verb)
    if debug:
        print(f"Found {len(verbs)} verbs as {verbs}")

    for syn in [syn for syn in synonyms.keys() if syn not in verbs]:
        print(f"WARNING: Why have verb synonyms {synonyms[syn]} without a defined syntax for the verb?")
    return verbs

#
# Return a map of noun-IDs to sets of noun synonyms and descriptions
# NOTE: The noun-ID may be a nonce that isn't human readable
#
def find_syntax_object(filenames):
    desc_objs = {}
    def process_obj_desc(dict, match):
        obj = match[0].lower()
        desc = match[1]
        if isgood(obj) and dict.get(obj) == None:
            dict[obj] = set([desc])
    obj_desc_pattern = re.compile(r'^<OBJECT ([^<>]+?)\s[^<>]+?\(DESC "([^<>"]+?)"\)[^<>]*?>', flags=re.DOTALL|re.MULTILINE)
    process_pattern(filenames, "obj_desc", obj_desc_pattern, desc_objs, process_obj_desc)

    def process_obj_synonym(dict, match):
        obj = match[0].lower()
        syns = [syn.lower() for syn in match[1].split() if isgood(syn)]
        if dict.get(obj) == None:
            if debug:
                print(f"WARNING: {obj} has synonyms {syns} but no description")
            dict[obj] = set([])
        if isgood(obj):
            for i, item in enumerate(syns):
                if item[:1] == ';':
                    syns = syns[:i]
                    break
            dict[obj] = dict[obj].union(set(syns))
        if debug:
            print(f"{obj} '{dict[obj][0]}' is {dict[obj][1:]}")
    obj_syns_pattern = re.compile(r'^<OBJECT ([^<>]+?)\s[^<>]+?\(SYNONYM ([^<>]+?)\)[^<>]*?>', flags=re.DOTALL|re.MULTILINE)
    process_pattern(filenames, "obj_synonym", obj_syns_pattern, desc_objs, process_obj_synonym)

    if debug:
        print(f"Found {len(desc_objs)} nouns as {desc_objs}")
    return desc_objs

#
# Return a set of room names (e.g., "West of House")
#
def find_syntax_rooms(filenames):
    room_objs = {}
    def process_obj_room(dict, match):
        obj = match[0].lower()
        if isgood(obj) and dict.get(obj) == None:
            desc = match[1]
            dict[obj] = desc
    obj_room_pattern = re.compile(r'^<ROOM ([^\s]+?)\s[^<>]+?\(DESC "([^<>"]+?)"\)[^<>]*?>', flags=re.DOTALL|re.MULTILINE)
    process_pattern(filenames, "obj_room", obj_room_pattern, room_objs, process_obj_room)
    # later games used (LOC ROOMS)
    obj_room_pattern = re.compile(r'^<OBJECT ([^<>]+?)\s[^<>]+?\(LOC ROOMS\)[^<>]+?\(DESC "([^<>"]+?)"\)', flags=re.DOTALL|re.MULTILINE)
    process_pattern(filenames, "obj_room", obj_room_pattern, room_objs, process_obj_room)

    if debug:
        print(f"Found {len(room_objs)} rooms as {room_objs}")
    rooms = set(room_objs.values())
    return rooms


# Command-line: syntax.py gamename gamefiles*.zil
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Exclude script name and the first argument, which is the game name
        gamename = sys.argv[1]
        filenames = sys.argv[2:]
        verbs = find_syntax_verbs(filenames)
        objs = find_syntax_object(filenames)
        rooms = find_syntax_rooms(filenames)

        print(f"# Config for {gamename.upper()}, in LLM style")
        print(f"#")
        print(f"#\n")
        print(f"[game]")
        print(f'path = "./infocom/{gamename}/COMPILED/{gamename}.z3"\n')
        print(f"setup = '''\n{gamename} is a text-based adventure game from Infocom.\n'''\n")
        print(f"background_files = [\n]\n")
        print(f"background_urls = [\n]\n")
        print(f"walkthrough_urls = [\n]\n")

        print("[syntax]")
        print("verbs = [")
        dedup = set([])
        for vstrs in [[f'"{v}"' for v in verbs] for verbs in verbs.values()]:
            s = f"    [ {', '.join(vstrs)} ],"
            if not s in dedup:
                print(s)
                dedup.add(s) # silly dedup hack
        print("] # verbs\n")

        print("nouns = [")
        dedup = set([])
        for nstrs in [[f'"{n}"' for n in objs] for objs in objs.values()]:
            s = f"    [ {', '.join(nstrs)} ],"
            if not s in dedup:
                print(s)
                dedup.add(s) # silly dedup hack
        print("] # nouns\n")

        print("rooms = [")
        for rstr in [f'"{room}"' for room in rooms]:
            print(f"    {rstr},")
        print("] # rooms\n")
    else:
        print("Please provide the filenames as arguments.")


