#!/usr/bin/python3.6

import random

import hashlib
import urllib.request
from PIL import Image
from pathlib import Path
from tempfile import NamedTemporaryFile
import random
import yaml

from db_context_manager import dbopen
from create_image import create_wtp_images

config_dir = Path.cwd().parent.joinpath("config.yaml")
config = yaml.safe_load(open(config_dir))

cachedir = config["cachedir"]


def get_random_pokemon(generations):
    """
    Args:
        generations (list): Contains ints with the wanted generation number(s).

    Returns:
        pokemon: a <dict> with 'pokemon' (the creature's name <str>) and 'id' (its id <str>).
    """
    with dbopen("pokemon.db") as c:
        gen = random.choice(generations)

        # Must use rowid, as id is technically text.
        c.execute("SELECT MIN(rowid) FROM pokemon WHERE gen=?;", [gen])
        lowest_id = c.fetchone()[0]

        c.execute("SELECT MAX(rowid) FROM pokemon WHERE gen=?;", [gen])
        highest_id = c.fetchone()[0]

        pokemon_id = random.randint(lowest_id, highest_id)
        c.execute("SELECT pokemon, id FROM pokemon WHERE id=?;", [str(pokemon_id)])
        result = c.fetchone()

        pokemon = {"name": result[0], "id": result[1]}

        return pokemon


def fetch_image(pokemon_id):
    def pad(pokemon_id):
        if len(pokemon_id) < 3:
            pokemon_id = "0" + pokemon_id
            pokemon_id = pad(pokemon_id)
        return pokemon_id

    pokemon_id = pad(pokemon_id)

    url = f"https://assets.pokemon.com/assets/cms2/img/pokedex/full/{pokemon_id}.png"

    # The first value is the path to the image's tempfile.
    image_path = urllib.request.urlretrieve(url)[0]

    return image_path


def cached_version_exists(pokemon, shrouded_path, unshrouded_path):
    if Path(shrouded_path).is_file() and Path(unshrouded_path).is_file():
        return True


def save_to_tempfile(image):
    tempfile = NamedTemporaryFile(suffix=".png", delete=False)
    image.save(tempfile.name, "PNG")

    return tempfile.name


def hash_pokemon_name(pokemon_name):
    """ Returns a 7-letter hash for a pokemon's name, thus obscuring it. """

    b = pokemon_name.encode()
    full_hash = hashlib.sha224(b).hexdigest()
    small_hash = full_hash[-7:]

    return small_hash


def get_pokemon_and_image(generations):
    """ Gets pokemon name, id, and WTP images (shrouded and not)

    Returns:
        dict: A dict that contains string 'name', id (a three-number string
            representing the pokemon's ID), 'shrouded_path', and 'unshrouded_path'
            (which contain the paths to their respective WTP images). Eg:

                {
                    'name': 'Pikachu',
                    'id': '025',
                    'shrouded_path': '<cache directory>/64f4cf1_shrouded.png',
                    'unshrouded_path': '<cache directory>/64f4cf1_unshrouded.png'
                }
    """
    poke_data = get_random_pokemon(generations)
    # poke_data = {'name': 'Pikachu', 'id': '025'} # Test case

    # Putting the real pokemon name as the filename allows Discord users to see
    # what the pokemon is
    name_hash = hash_pokemon_name(poke_data["name"])

    shrouded_path = f"{cachedir}/{name_hash}_shrouded.png"
    unshrouded_path = f"{cachedir}/{name_hash}_unshrouded.png"

    if cached_version_exists(poke_data, shrouded_path, unshrouded_path):
        shrouded_image = Image.open(shrouded_path)
        unshrouded_image = Image.open(unshrouded_path)
    else:
        # Create images from pokedex
        image_path = fetch_image(poke_data["id"])
        shrouded_image, unshrouded_image = create_wtp_images(image_path)

        # Saved cached versions
        shrouded_image.save(shrouded_path, "PNG")
        unshrouded_image.save(unshrouded_path, "PNG")

    poke_data["shrouded_path"] = shrouded_path
    poke_data["unshrouded_path"] = unshrouded_path

    return poke_data
