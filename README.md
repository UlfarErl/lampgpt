# lampgpt
An LLM-enchanced Infocom Experience

## Summary
The Infocom text adventures—especially the early ones—were by necessity rather content poor,
with sparse vocabularies, terse descriptions, and very limited interaction possibilities, 
with stock responses like _'There is nothing special about...'_ being very common.

Modern LLM chatbots should be able to fix the above limitations and allow richer gameplay
than was possible in the games as they were originally created, while still conforming to the 
spirit, style, and storyline of the game.

In particular, LLMs should allow much richer input capabilities, with pretty much any text input
being recognized and either (1) turned into an input that the parser accepts, or (2) have the
LLM itself respond with something better than _'There's nothing special about...'_.
**STATUS: Input rewriting is unimplemented, but invalid inputs such as _'Chew your nails'_ get good responses.**

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

echo 'OPENAI_API_KEY=PUT_YOUR_API_KEY_HERE' > .env
./lampgpt.py -t zork1.log -S hardyboys zork1
./lampgpt.py -t starcross.log starcross
```

## Example Transcripts
There are some transcripts of examples of gameplay in the playlogs directory.
For example, below is a section from Starcross in the style of a high space opera.

> |> **starboard**  
> Storage Chamber You've ventured into the compact storage chamber of the
> Starcross, a repository of tools and gear essential for the intrepid explorer.
> The only passage retreats to port, back towards the heart of the ship. Suspended
> on a rack, your space suit awaits, a sentinel of fabric and metal poised for
> adventure beyond the confines of this vessel. Beside it, a safety line dangles
> from the wall, a slender thread that ties you to the safety of the Starcross
> amidst the vast ballet of the cosmos. Here, in this small cubicle, lies the
> equipment that bridges the gap between the known and the unknown, ready to
> accompany you into the starry expanse.
> 
> |> **bite my nails**  
> In the grand expanse of the cosmos, with mysteries untold and adventures
> unnumbered waiting just beyond the bulkhead, you find a moment of introspection,
> a brief pause in the relentless march of destiny. Yet, as you contemplate the
> universe and your place within it, you realize that some habits of terrestrial
> life, such as biting one's nails, hold little sway in the face of the infinite.
> There are worlds to explore, secrets to uncover, and the vast unknown calls to
> you, urging you to look outward, to the stars, rather than inward.
> 
> |> **perform calisthenic exercises**  
> In the vast expanse of space, aboard the Starcross, your desire to maintain
> physical fitness is commendable. Though the ship's confines may limit the
> grandeur of calisthenic exercises you might envision, you find a way to adapt,
> performing stretches and basic routines in the limited space. Your actions,
> though small in the grand scheme of the cosmos, are a testament to the human
> spirit's adaptability and determination to thrive, even in the most unlikely of
> environments.
 
 ## TODO
- **Other LLMs**: Support local LLMs such as Ollama.
- **Cheaper**: Make the prompts shorter and repeated far less. 
- **Input rewriting**: Make the LLMs understand the grammar and vocabulary of the game, and try to rewrite player inputs into commands in that language.
- **Stateless exploration**: Use the save/restore or undo meta-command features of `bocfel` to try various commands and provide them and their output to the LLMs as extra context.