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

Also, the LLMs should be able to augment the details of the players surroundings, objects,
and NPCs, in ways that make even description-barren games like **Starcross** have rich
textual atmosphere of **Wishbringer** and other later games.

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
echo 'ANTHROPIC_API_KEY=PUT_YOUR_API_KEY_HERE' > .env
./lampgpt.py -t zork1.log -S hardyboys zork1
./lampgpt.py -t starcross.log -original starcross
```

## Playing with an "Ultimate Parser"
To play the Infocom games in their original form, and just make use of LLMs to "fix" any limitations
in the parser, you can use `./lampgpt.py -O gamename` where `-O` is short for original. 
This style of playing works very well with ChatGPT4 and is also very fast and cheap
(albeit not out of control) because the LLM is only consulted upon parser errors.  Below is
an example of the LLM fixing an absurdly convoluted command from the start of Zork1.
(This LLM response isn't shown to the player—only the fixed command in triple plusses is used.)

> **West of House**  
> You are standing in an open field west of a white house, with a boarded front door.  
> There is a small mailbox here.  
> 
> |> **summon all of your strength and tear up the infernal receptacle of blasphemous communications**  
> The player's original command was a vivid and imaginative attempt to interact with 
> the game environment in a specific and dramatic way. The command aimed to 
> forcefully destroy the mailbox. However, 
> due to the game's limitations in understanding complex and thematic language, we 
> need to simplify the command while retaining the essence of the action desired.
> 
> 1. "attack" or "smash" - These verbs are understood by the game and convey the 
> intent of using force to destroy or damage an object. "Smash" is particularly fitting as 
> it suggests a strong, destructive action, closely matching the player's original intent.
> 
> 2. "small mailbox" or "mailbox" - This is the object the player intends to interact with.
> The game recognizes "small mailbox" or "mailbox" as valid noun phrases for this object.
> 
> By using these words, we can formulate a command that the game engine 
> is capable of understanding, while still attempting to fulfill the player's original 
> intention as closely as possible. Here's a suggested new command that aligns
> with the game's vocabulary and the player's intent:
> 
> +++**smash mailbox**+++

## Example Transcripts
There are some transcripts of examples of gameplay in the `playlogs` and `walkthroughs` directories.
Here are a couple of good examples from Zork1 when playing in a Terry Pratchett style:  
> |> **move rug**  
> Summoning every ounce of your strength and channeling the spirit of a thousand
> interior decorators, you heave the rug aside.  
  
> |> **get coffin**  
> With a grunt that would make your gym teacher proud, you hoist the gold coffin
> onto your shoulders. It's heavier than your last relationship and nearly as
> complicated to handle, but you manage.

As another example, below is a section from Starcross in the style of a high space opera.  
> |> **starboard**  
> Storage Chamber  
> You've ventured into the compact storage chamber of the
> Starcross, a repository of tools and gear essential for the intrepid explorer.
> The only passage retreats to port, back towards the heart of the ship. Suspended
> on a rack, your space suit awaits, a sentinel of fabric and metal poised for
> adventure beyond the confines of this vessel. Beside it, a safety line dangles
> from the wall, a slender thread that ties you to the safety of the Starcross
> amidst the vast ballet of the cosmos. Here, in this small cubicle, lies the
> equipment that bridges the gap between the known and the unknown, ready to
> accompany you into the starry expanse.
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
- **Stateless exploration**: Use the save/restore or undo meta-command features of `bocfel` to try various commands and provide them and their output to the LLMs as extra context.
- **Side-by-side mode**: Use `curses` or something similar for side-by-side playing of the original and LLM-rewritten game.

## DONE
- **Other LLMs**: Support Gemini and Claude.
- **Other LLMs**: Support local LLMs via Ollama. (Alas, they aren't really good enough...)
- **Cheaper**: Make the prompts shorter and repeated far less. Limit the prompt to the last 10 to 20 game commands and responses.
- **Input rewriting**: Make the LLMs understand the grammar and vocabulary of the game, and try to rewrite player inputs into commands in that language.
- **Parser rewriting only**: The `-original` mode allows existing games to be played unmodified, just with a better parser.
