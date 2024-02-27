# lampgpt
An LLM-enchanced Infocom Experience

## Summary
The Infocom text adventures---especially the early ones---were by necessity rather content poor,
with limited vocabularies, terse descriptions, and very limited interaction possibilities, 
with stock responses like _'There is nothing special about...'_ being very common.

Modern LLM chatbots should be able to fix the above limitations and allow richer gameplay
than was possible in the games as they were originally created, while still conforming to the 
spirit, style, and storyline of the game.

In particular, LLMs should allow much richer input capabilities, with pretty much any text input
being recognized and either (1) turned into an input that the parser accepts, or (2) have the
LLM itself respond with something better than _'There's nothing special about...'_.
**STATUS: Input rewriting is unimplemented, we get good 
responses to invalid inputs such as _'Chew your nails'_.**

Also, the LLMs should be able to augment the details of the players surroundings, objects,
and NPCs, in ways that make even description-barren games like **Starcross** have rich
textual atmosphere of **Wishbringer** and other later games.
**STATUS: This works pretty well already.**

## Setup
```
git clone git@github.com:UlfarErl/lampgpt.git
cd lampgpt

git submodule init
git submodule update bocfel
git submodule update infocom/zork1
git submodule update infocom/starcross
# to get all the games, just do 'git submodule update'

tar xvfz ./bocfel/downloads/bocfel-2.1.2.tar.gz
cd bocfel-2.1.2
cp ../bocfel_config.mk config.mk
make
cd ..

OPENAI_API_KEY=PUT_YOUR_API_KEY_HERE ./lampgpt.py -t zork1.log -S hardyboys zork1
OPENAI_API_KEY=PUT_YOUR_API_KEY_HERE ./lampgpt.py -t starcross.log starcross
```

## TODO
- **Other LLMs**: Support Vertex AI, Gemini, and Ollama.
- **Cheaper**: Make the prompts shorter and repeated far less. 
- **Input rewriting**: Make the LLMs understand the grammar and vocabulary of the game, and try to rewrite player inputs into commands in that language.
- **Stateless exploration**: Use the save/restore or undo meta-command features of `bocfel` to try various commands and provide them and their output to the LLMs as extra context.