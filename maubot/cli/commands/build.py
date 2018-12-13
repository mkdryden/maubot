# maubot - A plugin-based Matrix bot system.
# Copyright (C) 2018 Tulir Asokan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
from typing import Optional
from io import BytesIO
import zipfile
import os

from mautrix.client.api.types.util import SerializerError
from ruamel.yaml import YAML, YAMLError
from colorama import Fore, Style
from PyInquirer import prompt
import click

from ...loader import PluginMeta
from ..base import app
from ..cliq.validators import PathValidator

yaml = YAML()


def zipdir(zip, dir):
    for root, dirs, files in os.walk(dir):
        for file in files:
            zip.write(os.path.join(root, file))


def read_meta(path: str) -> Optional[PluginMeta]:
    try:
        with open(os.path.join(path, "maubot.yaml")) as meta_file:
            try:
                meta_dict = yaml.load(meta_file)
            except YAMLError as e:
                print(Fore.RED + "Failed to build plugin: Metadata file is not YAML")
                print(Fore.RED + str(e) + Style.RESET_ALL)
                return None
    except FileNotFoundError:
        print(Fore.RED + "Failed to build plugin: Metadata file not found" + Style.RESET_ALL)
        return None
    try:
        meta = PluginMeta.deserialize(meta_dict)
    except SerializerError as e:
        print(Fore.RED + "Failed to build plugin: Metadata file is not valid")
        print(Fore.RED + str(e) + Style.RESET_ALL)
        return None
    return meta


def read_output_path(output: str, meta: PluginMeta) -> Optional[str]:
    directory = os.getcwd()
    filename = f"{meta.id}-v{meta.version}.mbp"
    if not output:
        output = os.path.join(directory, filename)
    elif os.path.isdir(output):
        output = os.path.join(output, filename)
    elif os.path.exists(output):
        override = prompt({
            "type": "confirm",
            "name": "override",
            "message": f"{output} exists, override?"
        })["override"]
        if not override:
            return None
        os.remove(output)
    return os.path.abspath(output)


def write_plugin(meta: PluginMeta, output: str) -> None:
    with zipfile.ZipFile(output, "w") as zip:
        meta_dump = BytesIO()
        yaml.dump(meta.serialize(), meta_dump)
        zip.writestr("maubot.yaml", meta_dump.getvalue())

        for module in meta.modules:
            if os.path.isfile(f"{module}.py"):
                zip.write(f"{module}.py")
            elif os.path.isdir(module):
                zipdir(zip, module)
            else:
                print(Fore.YELLOW + f"Module {module} not found, skipping")

        for file in meta.extra_files:
            zip.write(file)


@app.command(short_help="Build a maubot plugin",
             help="Build a maubot plugin. First parameter is the path to root of the plugin "
                  "to build. You can also use --output to specify output file.")
@click.argument("path", default=os.getcwd())
@click.option("-o", "--output", help="Path to output built plugin to",
              type=PathValidator.click_type)
@click.option("-u", "--upload", help="Upload plugin to main server after building", is_flag=True,
              default=False)
def build(path: str, output: str, upload: bool) -> None:
    meta = read_meta(path)
    output = read_output_path(output, meta)
    if not output:
        return
    os.chdir(path)
    write_plugin(meta, output)
    print(Fore.GREEN + "Plugin build complete.")
